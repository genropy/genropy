import pytest
import gnr.web.jsmin as gj

class TestJsMin():
    def test_jsmin(self):
        r = gj.jsmin("");
        assert not r 

        j = "console.log('hello');"
        r = gj.jsmin(j)
        assert r==j

        r = gj.jsmin(f"{j} ")
        assert r is not j
        assert " " not in r
        
        r = gj.jsmin(f"{j}\n")
        assert r is not j
        assert "\n" not in r

        r = gj.jsmin(f"{j}\r")
        assert r is not j
        assert "\r" not in r

        # test peek on comments
        r = gj.jsmin("var a = 1; // balla ")
        assert "balla" not in r
        r = gj.jsmin("var a = 1; /* balla */")
        assert "balla" not in r
        with pytest.raises(gj.UnterminatedComment):
            r = gj.jsmin("var a = 1; /* balla")

        # test ops
        r = gj.jsmin("var a =1; \n { console.log(a); }\n")
        assert "\n" not in r
        with pytest.raises(gj.UnterminatedRegularExpression):
            r = gj.jsmin("var a =1; \n /{ console.log")

        r = gj.jsmin("""var a =1; \n { console.log\t [  """)
        assert "\t" not in r

        
    def test_isAlphanum(self):
        assert gj.isAlphanum('d')
        assert gj.isAlphanum('2')
        assert gj.isAlphanum('20')
        assert gj.isAlphanum('_')
        assert gj.isAlphanum('$')
        assert gj.isAlphanum('¤')
        
        with pytest.raises(TypeError):
            assert gj.isAlphanum(None)

        
        
