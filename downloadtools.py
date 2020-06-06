import sys
import os
import urllib.request
import time
import tempfile
import zipfile
import googlerepo

path = googlerepo.getSDKPath()

if(len(sys.argv) < 2):
    repo = googlerepo.Repository()
    repo.listPackages()
for pkgrequest in sys.argv[1:]:
    repo = googlerepo.Repository()
    try:
        pkgname,pkgurl,xml = repo.getNewestPackage(pkgrequest)
    except googlerepo.UserDidNotAccept:
        print("Skipping.")
        continue
    except googlerepo.CouldNotFindPackage:
        print("Couldn't find package " + pkgrequest)
        continue

    pkgname = pkgname.split(';')
    pkgbase = pkgname[-1]
    if(len(pkgname) > 1):
        pkgpath = os.sep.join(pkgname[:-1])
    else:
        pkgpath = ''

    print('Downloading ' + os.path.basename(pkgurl))

    with urllib.request.urlopen(pkgurl) as response, open(os.path.join(tempfile.gettempdir(),os.path.basename(pkgurl)),'wb') as out_file:
        data = response.read()
        out_file.write(data)
        out_file.flush()
        fn = out_file.name

    path = os.path.join(path,pkgpath)

    try:
        os.makedirs(path)
    except FileExistsError:
        pass
    with zipfile.ZipFile(fn,"r") as zip_ref:
        print('Unzipping ' + os.path.basename(pkgurl))
        pkgbase = zip_ref.namelist()[0].split('/')[0]
        zip_ref.extractall(path)

    if pkgbase != "tools":
        with open(os.path.join(path,pkgbase,'package.xml'),'w') as f:
            f.write(xml)