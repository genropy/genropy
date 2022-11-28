# -*- coding: utf-8 -*-
#
#  Copyright (c) 2022 Softwell. All rights reserved.

from gnr.core.gnrbaseservice import GnrBaseService
import boto3, io
from PIL import Image, ImageDraw

class Main(GnrBaseService):
    def __init__(self, bucket=None, region=None, **kwargs):
        self.bucket = 'sicis-bucket'
        self.region = 'eu-central-1'  
    
    def processTextAnalysis(self, document=None):
        #Get the document from S3
        s3_connection = boto3.resource('s3')

        s3_object = s3_connection.Object(self.bucket,document)
        s3_response = s3_object.get()

        stream = io.BytesIO(s3_response['Body'].read())
        image=Image.open(stream)

        # Analyze the document
        client = boto3.client('textract', region_name=self.region)

        image_binary = stream.getvalue()
        response = client.analyze_document(Document={'Bytes': image_binary},
            FeatureTypes=["TABLES", "FORMS"])

        ### Uncomment to process using S3 object ###
        response = client.analyze_document(
            Document={'S3Object': {'Bucket': self.bucket, 'Name': self.document}},
            FeatureTypes=["TABLES", "FORMS"])

        #Get the text blocks
        blocks=response['Blocks']
        width, height =image.size    
        print ('Detected Document Text')
    
        # Create image showing bounding box/polygon the detected lines/text
        for block in blocks:
            self.DisplayBlockInformation(block)    
            draw=ImageDraw.Draw(image)

            # Draw bounding boxes for different detected response objects
            if block['BlockType'] == "KEY_VALUE_SET":
                if block['EntityTypes'][0] == "KEY":
                    self.ShowBoundingBox(draw, block['Geometry']['BoundingBox'],width,height,'red')
                else:
                    self.ShowBoundingBox(draw, block['Geometry']['BoundingBox'],width,height,'green')             
            if block['BlockType'] == 'TABLE':
                self.ShowBoundingBox(draw, block['Geometry']['BoundingBox'],width,height, 'blue')
            if block['BlockType'] == 'CELL':
                self.ShowBoundingBox(draw, block['Geometry']['BoundingBox'],width,height, 'yellow')
            if block['BlockType'] == 'SELECTION_ELEMENT':
                if block['SelectionStatus'] =='SELECTED':
                    self.ShowSelectedElement(draw, block['Geometry']['BoundingBox'],width,height, 'blue')    

        # Display the image
        image.show()
        print(x)
        return len(blocks)

    def ShowBoundingBox(draw,box,width,height,boxColor):
        left = width * box['Left']
        top = height * box['Top'] 
        draw.rectangle([left,top, left + (width * box['Width']), top +(height * box['Height'])],outline=boxColor)       

    def ShowSelectedElement(draw,box,width,height,boxColor):
        left = width * box['Left']
        top = height * box['Top'] 
        draw.rectangle([left,top, left + (width * box['Width']), top +(height * box['Height'])],fill=boxColor)      

    # Displays information about a block returned by text detection and text analysis
    def DisplayBlockInformation(block):
        print('Id: {}'.format(block['Id']))
        if 'Text' in block:
            print('    Detected: ' + block['Text'])
        print('    Type: ' + block['BlockType'])
    
        if 'Confidence' in block:
            print('    Confidence: ' + "{:.2f}".format(block['Confidence']) + "%")  

        if block['BlockType'] == 'CELL':
            print("    Cell information")
            print("        Column:" + str(block['ColumnIndex']))
            print("        Row:" + str(block['RowIndex']))
            print("        Column Span:" + str(block['ColumnSpan']))
            print("        RowSpan:" + str(block['ColumnSpan']))    

        if 'Relationships' in block:
            print('    Relationships: {}'.format(block['Relationships']))
        print('    Geometry: ')
        print('        Bounding Box: {}'.format(block['Geometry']['BoundingBox']))
        print('        Polygon: {}'.format(block['Geometry']['Polygon']))

        if block['BlockType'] == "KEY_VALUE_SET":
            print ('    Entity Type: ' + block['EntityTypes'][0])

        if block['BlockType'] == 'SELECTION_ELEMENT':
            print('    Selection element detected: ', end='')   

            if block['SelectionStatus'] =='SELECTED':
                print('Selected')
            else:
                print('Not selected')    

        if 'Page' in block:
            print('Page: ' + block['Page'])
        print()