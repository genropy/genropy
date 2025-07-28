# -*- coding: utf-8 -*-
from PIL import Image
from urllib.parse import urlparse,parse_qs
import base64
from io import BytesIO      
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
        remove_img = fb.button('Remove', hidden='^.image?=!#v')
        #remove_img.dataController('SET .image = null;') 
        #this removes stored value but doesn't delete file on server
        remove_img.dataRpc(self.deleteImage, file_url='=.image', _onResult="SET .image=null;")

    @public_method
    def deleteImage(self, file_url=None, **kwargs):
        path_list = self.site.pathListFromUrl(file_url)
        fileSn = self.site.storageNodeFromPathList(path_list)
        fileSn.delete()
        print('**DELETED IMAGE: ', file_url)
        return 'Image deleted'

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
        left.button('CONVERT').dataRpc('.dataurl', self.convertImageToDataUrl, image_url='=.image')
        bc.contentPane(region='center', float='right').img(src='^.dataurl', 
                                    width='150px', height='150px', hidden='^.dataurl?=!#v')

    @public_method
    def convertImageToDataUrl(self, image_url=None):
        img_cropdata = parse_qs(urlparse(image_url).query) 
        path_list = self.site.pathListFromUrl(image_url)
        img_path = self.site.storageNodeFromPathList(path_list).internal_path   #s3?
        
        im = Image.open(img_path)
        format = im.format
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
        left_offset = 1 if x < 0 else 0.5
        left = int(w/2 + x*left_offset - width/2)
        top = int(h/2 + y - height/2)
        right = int(left + width)
        bottom = int(top + height)
        im1 = im1.crop((left, top, right, bottom))
        buffered = BytesIO()
        im1.save(buffered, format=format)
        data_url = base64.b64encode(buffered.getvalue())
        return ','.join([f'data:image/{format};base64', data_url.decode()])
