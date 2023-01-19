# -*- coding: utf-8 -*-
import re,os
from gnr.core.gnrdecorator import public_method

"Test img"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull" 

    def test_0_imgUrl(self,pane):
        "Basic usage to display an image from an url"
        pane.textbox('^.image_url', width='100%', 
                    default='https://www.genropy.org/wp-content/themes/logo/genropy-logo.png')
        pane.div(background='#1e3055', height='60px', width='200px').img(
                    src='^.image_url', 
                    width='180px', height='40px', padding='10px')

    def test_1_uploadImage(self,pane):
        "Upload image or take picture and display it. Keep shift+clic pressed after upload to adjust cropping"
        pane.div(border='2px dotted silver', width='150px', height='150px').img(
                    src='^.image', 
                    crop_width='150px',
                    crop_height='150px',
                    edit=True, 
                    takePicture=True,
                    placeholder=True,
                    upload_filename='test_image', 
                    upload_folder='site:tests/image')

    def test_2_uploadCamera(self,pane):
        "Upload image from camera and advanced cropping procedure"
        pane.div(border='2px dotted silver', width='150px', height='150px').img(
                    src='^.image', 
                    crop_width='150px',
                    crop_height='150px',
                    edit=True,
                    placeholder=True,
                    upload_filename='test_image', 
                    upload_folder='*')

    def test_3_uploadImageAndRemove(self, pane):
        "Upload image and display it, but with possibility to remove data and file on server"
        pane.div('Double click or drag image and video here to upload')
        fb = pane.formbuilder(cols=1, margin_top='10px')
        fb.textbox('^.filename', lbl='Insert filename before uploading', default='test_image')
        fb.div(border='2px dotted silver').img(src='^.image', 
                    max_width='320px', width='320px',
                    max_height='168px', height='320px',
                    edit=True, 
                    placeholder='https://www.genropy.org/img/placeholder_image.jpg',
                    upload_filename='^.filename', 
                    upload_folder='site:tests/image')
        fb.dataRpc('.image_path', self.uploadImagePath, image='^.image', _if='image',
                        _userChanges=True, _fired='^run_image')
        remove_img = fb.button('Remove', hidden='^.image?=!#v')
        #remove_img.dataController('SET .image = null;') 
        #this removes stored value but doesn't delete file on server
        remove_img.dataRpc(self.deleteImage, file_path='=.image_path')
    
    @public_method
    def uploadImagePath(self, image):
        image_path = self.sitepath + re.sub('/_storage/site', '', image).split('?',1)[0]
        self.clientPublish('floating_message', message='Image Upload completed')  
        print('**UPLOADED IMAGE: ', image_path)
        return image_path

    @public_method
    def deleteImage(self, file_path=None, **kwargs):
        os.remove(file_path)
        self.setInClientData(value=None, path='test.test_2_uploadImageAndRemove.image')
        self.setInClientData(value=None, path='test.test_2_uploadImageAndRemove.image_path')
        print('**DELETED IMAGE: ', file_path)

    def test_4_s3Storage(self,pane):
        """Store img on S3 bucket. Please create a "s3_test" named aws_s3 storage service first"""
        pane.div(border='2px dotted silver', width='150px', height='150px').img(
                    src='^.image', 
                    crop_width='150px',
                    crop_height='150px',
                    edit=True, 
                    placeholder=True,
                    upload_filename='test_image', 
                    upload_folder='s3_test:img_test')

    def test_5_dataUrl(self, pane):
        """Here you can convert an image saved to filesystem to a bytestring."""
        bc = pane.borderContainer(height='200px')
        left = bc.contentPane(region='left', width='200px')
        left.div(border='2px dotted silver', width='150px', height='150px').img(
                    src='^.image', 
                    crop_width='150px',
                    crop_height='150px',
                    edit=True, 
                    placeholder=True,
                    upload_filename='test_image.jpg', 
                    upload_folder='site:tests/image')
        left.button('CONVERT').dataRpc('.dataurl', self.convertImageToDataUrl, imagepath='=.image')
        bc.contentPane(region='center', float='right').img(src='^.dataurl', 
                                    width='150px', height='150px', hidden='^.dataurl?=!#v')

    @public_method
    def convertImageToDataUrl(self, imagepath=None):
        from PIL import Image
        from urllib.parse import urlparse, parse_qs, urlsplit
        import base64
        from io import BytesIO      

        parsed_url = urlsplit(imagepath.strip('/'))
        img_cropdata = parse_qs(urlparse(imagepath).query) 
        path_list = parsed_url.path.split('/')
        img_path = self.site.storageNodeFromPathList(path_list).internal_path
        
        im = Image.open(img_path)
        width = int(img_cropdata['v_w'][0])
        height = int(img_cropdata['v_h'][0])
        z = float(img_cropdata['v_z'][0])
        x = float(img_cropdata['v_x'][0])
        y = float(img_cropdata['v_y'][0])
        r = -int(img_cropdata['v_r'][0])
        w = int(width * z)
        h = int(height * z)
        im1 = im.resize((w,h))
        im1 = im1.rotate(r)
        left = int(w/2 + x - width/2)
        top = int(h/2 + y - height/2)
        right = int(left + width)
        bottom = int(top + height)
        im1 = im1.crop((left, top, right, bottom))
        buffered = BytesIO()
        im1.save(buffered, format="JPEG")
        data_url = base64.b64encode(buffered.getvalue())
        return ','.join(['data:image/jpeg;base64', data_url.decode()])