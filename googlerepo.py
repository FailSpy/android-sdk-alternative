import sys
import urllib.request
import os
from xml.dom import Node
from xml.dom.minidom import parse
import re
import hashlib
import string

html_unescape_table = {
"&amp;":  "&",
"&quot;": '"',
"&apos;": "'",
"&gt;":   ">",
"&lt;":   "<",
}
def unescape(text):
    for k,v in html_unescape_table.items():
        text = text.replace(k,v)
    return text

class UserDidNotAccept(Exception):
    pass

class CouldNotFindPackage(Exception):
    pass

repos = ["repository2-1.xml",
"addon2-1.xml",
"sys-img/google_apis_playstore/sys-img2-1.xml",
"sys-img/google_apis/sys-img2-1.xml",
"sys-img/android/sys-img2-1.xml",
"sys-img/android-wear/sys-img2-1.xml",
"sys-img/android-wear-cn/sys-img2-1.xml",
"sys-img/android-tv/sys-img2-1.xml",
"sys-img/android-automotive/sys-img2-1.xml"
]

baserepo = "https://dl.google.com/android/repository/"
class Repository:
    def __init__(self):
        self.nextRepo = 0
        self.baserepo = baserepo
        self.getNextRepo()
    
    def getNextRepo(self):
        self.baserepo = baserepo
        repodoc = repos[self.nextRepo]
        if os.path.basename(repodoc) != repodoc:
            # If the repo XML is in a subdirectory, all package downloads will be available from that subdirectory, so we specify baserepo vs repourl
            self.baserepo = os.path.join(self.baserepo,os.path.dirname(repodoc)) + '/'
            repodoc = os.path.basename(repodoc)

        self.repourl = self.baserepo + repodoc

        with urllib.request.urlopen(self.repourl) as r:
            self.repofile = parse(r)

        self.packages = self.repofile.getElementsByTagName('remotePackage')
        self.nextRepo += 1

    def listPackages(self):
        listed = []
        while(self.nextRepo < len(repos)):
            # This could obviously be a lot better, but that's what the actual SDK manager is for.
            for package in self.packages:
                pkgid = package.getAttribute('path')
                if pkgid not in listed:
                    print(pkgid)
                    listed.append(pkgid)
            self.getNextRepo()

    def generatePackageXml(self,pkg):
        # This is a hack attempt to make package.xml match the original SDK manager generated ones as *closely* as possible
        # Forgive me for I am about to commit sin, XML.

        localPackage = pkg.cloneNode(True)
        localPackage.tagName = 'localPackage'
        obsolete = localPackage.getAttribute('obsolete')
        localPackage.setAttribute('obsolete',obsolete if len(obsolete) > 0 else 'false')
        try:
            localPackage.removeChild(localPackage.getElementsByTagName('archives')[0])
        except ValueError:
            pass
        try:
            localPackage.removeChild(localPackage.getElementsByTagName('channelRef')[0])
        except ValueError:
            pass

        licensename = localPackage.getElementsByTagName('uses-license')[0].getAttribute('ref')
        # SDK ARM DBT license has a smart quote at char 7622 in its current form requiring this ascii encoding just so SDK manager doesn't complain.
        licensexml = unescape(self.getRawLicense(licensename).toxml('ascii').decode('ascii'))

        # Seriously, please forgive me.
        for child in self.repofile.childNodes:
            # Get the tag with all namespaces
            if(child.namespaceURI != None):
                nsTag = child
                break
        
        ns = {
            'http://schemas.android.com/repository/android/common/01': 'ns2',
            'http://schemas.android.com/repository/android/generic/01': 'ns3',
            'http://schemas.android.com/sdk/android/repo/addon2/01': 'ns4',
            'http://schemas.android.com/sdk/android/repo/repository2/01': 'ns5'
        }
        
        mappedNS = {}
        nscounter = 6
        for i in range(0,nsTag.attributes.length):
            # Android namespace building
            attribute = nsTag.attributes.item(i)
            isAndroidSchema = attribute.value.startswith('http://schemas.android.com')
            if isAndroidSchema and attribute.value not in ns:
                # Find any android schemas not included in the base namespaces
                ns[attribute.value] = 'ns'+str(nscounter)
                mappedNS[attribute.localName] = 'ns'+str(nscounter)
                nscounter += 1
            elif isAndroidSchema and attribute.localName not in mappedNS:
                # Map the schema localname to its new localname
                mappedNS[attribute.localName] = ns[attribute.value]
        
        typedetails = localPackage.getElementsByTagName('type-details')[0]
        typedetails.setAttribute("xmlns:xsi","http://www.w3.org/2001/XMLSchema-instance")

        # replace typedetails Namespace reference with the correct one i.e. 'common:genericDetailsType' becomes 'ns2:genericDetailsType'
        oldNS = typedetails.getAttribute('xsi:type').split(':')
        typedetails.setAttribute('xsi:type',mappedNS[oldNS[0]] + ':' + oldNS[1])

        localPackage.removeChild(localPackage.childNodes.item(1))
        localPackage = localPackage.toxml().replace('\n','').replace('\t','')

        # Finally, we're near the end.
        head = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        
        schemas = ' '.join(["xmlns:" + name + '="' + url + '"' for url,name in ns.items()])
        schemaTag = '<ns2:repository ' + schemas + '>'
        endTag = '</ns2:repository>'

        xml = head+schemaTag+licensexml+localPackage+endTag

        return xml

    def getPackageVersion(self,pkg,default=0):
        rev = pkg.getElementsByTagName('revision')[0]
        major = int(rev.getElementsByTagName('major')[0].firstChild.data.strip())
        minor = default
        try:
            minor = int(rev.getElementsByTagName('minor')[0].firstChild.data.strip())
            micro = int(rev.getElementsByTagName('micro')[0].firstChild.data.strip())
        except IndexError:
            micro = default
        
        return major,minor,micro

    def getNewestPackage(self,packagename,channel=3):
        # TODO: Add dependency handling.
        bestpkg = None
        version = 0
        for package in self.packages:
            if package.getAttribute('path').startswith(packagename):

                pkg_channel = int(package.getElementsByTagName('channelRef')[0].getAttribute('ref')[-1])
                if pkg_channel != 0 and pkg_channel != channel: 
                    # channel 0 will I think be the oldest version, so I'm assuming it'll get replaced if another channel is requested
                    pass
                
                rev = package.getElementsByTagName('revision')[0]
                major,minor,micro = self.getPackageVersion(package)
                
                v = major + (minor*.1) + (micro*.01)
                if(v > version):
                    bestpkg = package
                    version = v
        if bestpkg == None:
            if self.nextRepo < len(repos):
                self.getNextRepo()
                return self.getNewestPackage(packagename,channel)
            else:
                raise CouldNotFindPackage()

        lname,ltext = self.getPackageLicense(bestpkg)
        lhash = hashlib.sha1(ltext.encode('utf-8')).hexdigest()
        agreed = getLicenseAgreed(lhash)
        
        # Sorry, required to do so.
        if(not agreed):
            print(ltext)
            if not query_yes_no("Do you accept these terms?"):
                raise UserDidNotAccept()
            acceptLicense(lname,ltext)
        
        archives = bestpkg.getElementsByTagName('archive')
        pkgpath = bestpkg.getAttribute('path')
        if(len(archives) > 1):
            pkg = [pkg for pkg in bestpkg.getElementsByTagName('archive') if pkg.getElementsByTagName('host-os')[0].firstChild.data == getPlatform()][0]
        else:
            pkg = archives[0]
        pkgurl = self.baserepo + (pkg.getElementsByTagName('url')[0].firstChild.data)
        
        xml = self.generatePackageXml(bestpkg)
        
        print('Found package: ' + pkgpath)
        return pkgpath,pkgurl,xml

    def getRawLicense(self,licensename):
        for licensing in self.repofile.getElementsByTagName('license'):
            if licensing.getAttribute('id') == licensename:
                return licensing
        return None

    def getPackageLicense(self,package):
        licensename = package.getElementsByTagName('uses-license')[0].getAttribute('ref')
        licensetext = self.getRawLicense(licensename).firstChild.data
        return licensename,stripLicense(licensetext)
    

def getLicenseAgreed(licensehash):
    licensepath = os.path.join(getSDKPath(),'licenses')
    try:
        os.makedirs(licensepath)
    except FileExistsError:
        pass
    files = os.listdir(licensepath)
    for f in files:
        fpath = os.path.join(licensepath,f)
        if(os.path.isdir(fpath)):
            continue
        with open(fpath,'r') as f:
            l = f.read()
            l = l.split('\n')
            if l[-1].strip() == licensehash.strip():
                return True
    return False

def stripLicense(licensetext):
    #
    # https://github.com/JetBrains/adt-tools-base/blob/master/repository/src/main/java/com/android/repository/impl/meta/TrimStringAdapter.java#L41-L46
    #
    licensetext = re.sub(r"(?<=\\s)[ \t]*",r"",licensetext,flags=re.MULTILINE)
    licensetext = re.sub(r"(?<!\n)\n(?!\n)",r" ",licensetext,flags=re.MULTILINE)
    licensetext = re.sub(r" +",r" ",licensetext,flags=re.MULTILINE)
    return licensetext.strip()

def acceptLicense(licensename, licensetext):
    # Needs to loop through all files to see all hashes
    licensepath = os.path.join(getSDKPath(),'licenses',licensename)
    with open(licensepath,'w') as f:
        f.write(licensetext)
        f.write('\n'+(hashlib.sha1(licensetext.encode('utf-8')).hexdigest())) # How SDK Manager detects hashes

def getSDKPath():
    path = os.getenv('ANDROID_SDK_ROOT')
    if path == None:
        path = os.getenv('ANDROID_SDK_HOME')
        if path == None:
            print("Couldn't find ANDROID_SDK_ROOT or ANDROID_SDK_HOME")
            exit(1)
    return path

def getPlatform():
    # TODO: Add host-bits as a final detail
    if sys.platform == 'win32':
        platform = 'windows'
    elif sys.platform == 'darwin':
        platform = 'macosx'
    else:
        platform = sys.platform
    
    return platform
    


def query_yes_no(question):
    """Ask a yes/no question via input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    prompt = " [y/n] "

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")