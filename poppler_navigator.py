'''
A class for navigating a pdf file in python.

Dov Grobgeld <dov.grobgeld@gmail.com>
2021-03-20 Sat
'''

import os
import tempfile
from PIL import Image
from poppler import load_from_file, PageRenderer, RenderHint
from krita import *

class PopplerNavigor:
  def __init__(self,
               pdf_filename,
               image_filename=None,
               dpi=300):
    self.page_idx = 0
    if image_filename is not None:
      self.image_filename = image_filename
    else:
      self.tempdir = tempfile.TemporaryDirectory(prefix='popnav_')
    self.pdf_document = load_from_file(pdf_filename)    
    self.dpi = dpi
    self.current_page = None
    self.nodes = None
    self.doc = None
    self.qwindow = None
    self.set_page(self.page_idx)
    self.overlays = {} # Cached overlays

  def get_page_image_name(self):
    return self.tempdir.name + '/' + f'page_{self.page_idx}.png'
    
  def set_page(self,
               page_idx):
    '''Set a page and return the width height and image data'''

    # Keep the old overlay
    if self.nodes is not None and self.doc is not None:
      self.overlays[self.page_idx] = self.nodes[1].pixelData(0,0,self.doc.width(),self.doc.height())
    
    self.page_idx = page_idx

    page = self.pdf_document.create_page(self.page_idx)
    
    renderer = PageRenderer()
    renderer.set_render_hint(RenderHint.antialiasing,True) 
    renderer.set_render_hint(RenderHint.text_antialiasing,True)
    image = renderer.render_page(page,
                                 xres=self.dpi,
                                 yres=self.dpi,
                                 )
    self.current_page = (image.width,image.height,image.data)

    # Populate the background and the overlay
    if self.nodes is not None:
      # Update the background image
      self.nodes[0].setPixelData(image.data,0,0,image.width,image.height)

      # Clear the overlay
      overlay = self.overlays.get(self.page_idx,
                                  b'\0\0\0\0'*(image.width*image.height))
      self.nodes[1].setPixelData(overlay, 0,0,image.width,image.height)
      self.doc.refreshProjection()

      
  def get_current_page(self):
    return self.current_page

  def get_dpi(self):
    return self.dpi

  def next_page(self):
    if self.page_idx == self.pdf_document.pages-1:
      self.error_dialog('Already at last page')
      return
    
    self.set_page(self.page_idx+1)
    
  def prev_page(self):
    if self.page_idx == 0:
      self.error_dialog('Already at first page')
      return
    
    self.set_page(self.page_idx-1)

  def set_doc_and_nodes(self, doc, nodes):
    self.doc = doc
    self.nodes = nodes

  def set_qwindow(self, qwindow):
    self.qwindow = qwindow

  def error_dialog(self, message):
    QMessageBox.critical(self.qwindow,
                         'Error',
                         message)

if __name__=='__main__':
  import sys,os

  pdf_filename = sys.argv[1]
  page_idx = 5

  pn = PopplerNavigor(pdf_filename)
  pn.set_page(page_idx)
  img_filename = pn.get_page_image_name()
  os.system(f'cp {img_filename} /tmp/foo.png')
  
