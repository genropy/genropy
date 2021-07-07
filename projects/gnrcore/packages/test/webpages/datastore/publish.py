# -*- coding: utf-8 -*-

"""publish"""

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"

    def test_0_publish_subscribe(self, pane):
        "Press button to send generic message and check result in div and console"
        pane.textbox(value='^test')
        pane.button('publish', action='genro.publish("pressed",mypar,"foo")', mypar='=test', nodeId='BUTTON_1')
        #the button use genro.publish to 'send a generic message' 'pressed' with par mypar and 'foo'
        pane.dataController("""console.log('I receved subscription "pressed" ');
                               console.log('first par was:'+pressed[0]);
                               console.log('second par was:'+pressed[1]);""",
                            subscribe_pressed=True)
        pane.div(subscribe_test_pressed='var args =arguments; genro.bp(args);')
        #the data controller is triggered by subscribe_pressed and receives an array 'pressed' that
        #contains the published parameters
        

    def test_1_publish_subscribe_button(self, pane):
        "Press button to perform generic action and check result in console"
        pane.button('publish', action='PUBLISH pressed_2 = "bau","miao";')
        pane.dataController("console.log(pressed_2[0]); console.log(pressed_2[1]);",
                            subscribe_pressed_2=True)

    def test_2_publish_double_subscription(self, pane):
        "Press button to perform generic action and check result in console (double subscription)"
        pane.button('publish a', action='PUBLISH pressed_a = "bau","miao"')
        pane.button('publish b', action='PUBLISH pressed_b;')
        pane.dataController("""if(_reason=='pressed_a'){
                                    console.log('you pressed a '+pressed_a[0])}
                                else{
                                    console.log('you pressed b '+pressed_b[0])}""",
                                subscribe_pressed_a=True, subscribe_pressed_b=True)