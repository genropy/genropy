import os, os.path
import tempfile
import uuid
import getpass

from gnr.core import gnrsys as gs

def test_progress():
    from io import StringIO
    buf = StringIO()
    gs.progress(10,20, status="testing", fd=buf)
    buf.seek(0)
    res= buf.read()
    assert "50.0%" in res
    assert "="*30 in res

def test_mkdir():
    perms = [493, 511, 448, 509, 457, 449]
    tests_dir = [(str(uuid.uuid4()), perm) for perm in perms]
    with tempfile.TemporaryDirectory(dir=os.getenv("HOME")) as dname:
        for path, privileges in tests_dir:
            path_to_create = os.path.join(dname, path)
            gs.mkdir(path_to_create, privileges)
            assert os.path.exists(path_to_create)
            assert os.stat(path_to_create).st_mode & 0o777 == privileges

def test_expandpath():
    cur_user = getpass.getuser()
    user_home = os.getenv("HOME")
    t1 = gs.expandpath(f"~/foobar")
    assert user_home in t1
    t2 = gs.expandpath(f"~/foobar", full=True)
    assert user_home in t2
    
def test_listdirs():
    files = ['test1', 'test2', '.test3']
    with tempfile.TemporaryDirectory() as d:
        for fname in files:
            f = open(os.path.join(d, fname), "w")
            f.write(" ")
            f.close()
        # the original gnr.core.gnrsys.listdirs can't really work
        # res = gs.listdirs(d, invisible_files=False)
        # assert os.path.join(d, files[0]) in res
        # assert os.path.join(d, files[2]) not in res
        # res = gs.listdirs(d, invisible_files=True)
        # assert os.path.join(d, files[2]) in res

        # it always return an empty list
        res = gs.listdirs(d)
        assert not res

def test_resolvegenropypath():
    with tempfile.TemporaryDirectory(dir=os.getenv("HOME")) as d:
        bname = os.path.basename(d)
        test_file_name = "developers.txt"
        test_file = os.path.join(d, test_file_name)
        test_file_fd = open(test_file, "w")
        test_file_fd.write(" ")
        test_file_fd.close()
        paths = [
            f'~/{bname}/{test_file_name}',
            f'/{bname}/{test_file_name}',
            f'{d}/{test_file_name}',
            f'{bname}/{test_file_name}',
            os.path.relpath(d, os.getcwd()),
        ]
        for path in paths:
            res = gs.resolvegenropypath(path)
            assert res

        non_existing = gs.resolvegenropypath(str(uuid.uuid4()))
        assert not non_existing
        
        
