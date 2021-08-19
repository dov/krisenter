# A poppler based slide viwer for Krita.
#
# 2021-03-29 Mon
# Dov Grobgeld <dov.grobgeld@gmail.com>

import krita
from PIL import Image
from poppler.document import load_from_file
from poppler.pagerenderer import PageRenderer, RenderHint
import tempfile,os
import pikepdf

from PyQt5.QtWidgets import (
  QApplication,
  QDialog,
  QDialogButtonBox,
  QHBoxLayout,
  QLabel,
  QMainWindow,
  QPushButton,
  QVBoxLayout,
)
from krita import *

# An enum as a class
CLOSE_PRESENTATION = -1

def export_pdf(pdf_filename,
               output_pdf,
               doc):
  '''Export a pdf document through pikepdf'''
  pdf = pikepdf.Pdf.open(pdf_filename)

  root_node = doc.rootNode()
  nodes = root_node.childNodes()
  im_width,im_height = doc.width(),doc.height()
  dpi = 300 # TBD
  pt_width = im_width / dpi * 72
  pt_height = im_height / dpi * 72
  
  for page_idx,page in enumerate(pdf.pages):
    if page_idx+1 >= len(nodes):
      break

    # Convert the krita page to rgb and alpha
    pixeldata = nodes[page_idx+1].pixelData(0,0,im_width,im_height)
    rgba = Image.frombytes('RGBA', (im_width,im_height), pixeldata)
    alpha = rgba.getchannel('A')

    # No point in adding transparent image
    max_alpha = alpha.getextrema()[1]
    if max_alpha==0:
      print(f'Skipping empty page {page_idx+1}')
      continue

    print(f'Annotating page {page_idx+1}')

    rgb = Image.new("RGB", (im_width,im_height), (255, 255, 255))
    rgb.paste(rgba, mask=alpha)
    # Swap Red and Blue
    red,green,blue = rgb.split()
    rgb = Image.merge('RGB',[blue,green,red])

    if '/Resources' not in page:
      page['/Resources'] = pikepdf.Dictionary(XObject=pikepdf.Dictionary())
    elif '/XObject' not in page['/Resources']:
      page['/Resources']['/XObject'] = pikepdf.Dictionary()
    xobject = page['/Resources']['/XObject']

    # Find a free slot for our image
    n = 1
    prefix = None
    while prefix is None:
      candidate = f'/FX{n}'
      if candidate not in xobject:
        prefix = candidate
      else:
        n += 1

    print(f'prefix={prefix}')

    alpha_stream = pikepdf.Stream(pdf, alpha.tobytes())
    alpha_stream['/Type'] = pikepdf.Name('/XObject')
    alpha_stream['/Subtype'] = pikepdf.Name('/Image')
    alpha_stream['/ColorSpace'] = pikepdf.Name('/DeviceGray')
    alpha_stream['/BitsPerComponent'] = 8
    alpha_stream['/Interpolate'] = True
    alpha_stream['/Width'] = im_width
    alpha_stream['/Height'] = im_height
    
    rgb_stream = pikepdf.Stream(pdf, rgb.tobytes())
    rgb_stream['/Type'] = pikepdf.Name('/XObject')
    rgb_stream['/Subtype'] = pikepdf.Name('/Image')
    rgb_stream['/ColorSpace'] = pikepdf.Name('/DeviceRGB')
    rgb_stream['/BitsPerComponent'] = 8
    rgb_stream['/Interpolate'] = True
    rgb_stream['/SMask'] = alpha_stream
    rgb_stream['/Width'] = im_width
    rgb_stream['/Height'] = im_height
    
    fxo = pikepdf.Stream(pdf, b'q\n1 0 0 1 0 0 cm\n/Im Do\nQ\n')
    fxo['/Type'] = pikepdf.Name('/XObject')
    fxo['/Subtype'] = pikepdf.Name('/Form')
    fxo['/Resources'] = {
      '/XObject': {
      '/Im': rgb_stream,
      },
    }
    fxo['/BBox'] = [0, 0, im_width, im_height]
    
    png_content = f'''Q
q
{pt_width:.2f} 0 0 {pt_height:.2f} 0 0 cm
{prefix} Do
Q\n'''.encode()
    page.page_contents_add(pikepdf.Stream(pdf, 'q\n'.encode()), prepend=True)
    page.page_contents_add(pikepdf.Stream(pdf, png_content), prepend=False)
    if '/Resources' not in page:
      page['/Resources'] = pikepdf.Dictionary(XObject=pikepdf.Dictionary())
    elif '/XObject' not in page['/Resources']:
      page['/Resources']['/XObject'] = pikepdf.Dictionary()
    page['/Resources']['/XObject'][prefix] = fxo
    
  pdf.save(output_pdf)

# The existing pdf slide dialog
class KrisenterModifyDialog(QDialog):
  def __init__(self, pdf_filename=None, doc=None):
    super().__init__()

    self.setWindowTitle('Krisenter PDF')
    self.pdf_filename = pdf_filename
    self.doc = doc

    QBtn = QDialogButtonBox.Close

    self.buttonBox = QDialogButtonBox(QBtn)
    self.buttonBox.clicked.connect(self.clicked)

    self.layout = QVBoxLayout()

    export_button = QPushButton('Export')
    export_button.clicked.connect(self.export_dialog)
    self.layout.addWidget(export_button)

    close_presentation_button = QPushButton('Close Presentation')
    close_presentation_button.clicked.connect(self.close_presentation)
    self.layout.addWidget(close_presentation_button)

    self.layout.addWidget(self.buttonBox)
    self.setLayout(self.layout)

  def export_dialog(self):
    filename = QFileDialog.getSaveFileName()[0]
    export_pdf(self.pdf_filename,
               filename,
               self.doc)

  def close_presentation(self):
    dialog = QMessageBox()
    dialog.setIcon(QMessageBox.Question)
    dialog.setText('Are you sure you want to close the presentation?\n'
                   'Overlays will be lost')
    dialog.setWindowTitle('Confirmation')
    dialog.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    res = dialog.exec_()
 
    if res == QMessageBox.Ok:
      self.done(CLOSE_PRESENTATION)

  def clicked(self):
    self.done(0)

# The new pdf dialog
class KrisenterNewPdfDialog(QDialog):
  def __init__(self):
    super().__init__()

    self.setWindowTitle('Krisenter New PDF')
    self.pdf_filename = None

    QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

    self.buttonBox = QDialogButtonBox(QBtn)
    self.buttonBox.accepted.connect(self.accept)
    self.buttonBox.rejected.connect(self.reject)

    self.layout = QVBoxLayout()
    hlayout = QHBoxLayout()
    hlayout.addWidget(QLabel('Input PDF'))
    self.pdfLineEdit = QLineEdit('')    # The filename (read only)
    self.pdfLineEdit.setReadOnly(True)
    hlayout.addWidget(self.pdfLineEdit)
    self.pdfButton = QPushButton('...')
    self.pdfButton.clicked.connect(self.browse_pdf_filename)
    hlayout.addWidget(self.pdfButton)
    self.layout.addLayout(hlayout)
    self.layout.addWidget(self.buttonBox)
    self.setLayout(self.layout)

  def browse_pdf_filename(self):
    filename = QFileDialog.getOpenFileName()[0]
    self.pdfLineEdit.setText(os.path.basename(filename))
    self.pdf_filename = filename

  def get_pdf_filename(self):
    return self.pdf_filename

class PopplerNavigor:
  '''This class holds and navigates the pdf file. An instance of this class
  will be kept within the krita namespace.
  '''
  def __init__(self,
               pdf_filename,
               image_filename=None,
               dpi=300,
               qwindow=None):
    self.page_idx = 0
    self.pdf_filename = pdf_filename
    self.pdf_document = load_from_file(pdf_filename)
    self.dpi = dpi
    self.current_page = None
    self.background_node = None
    self.doc = None
    self.qwindow = qwindow
    self.page_idx = 0
    self.dummy_filename = tempfile.mktemp(suffix='.kra')
    self._create_krita_document()

  def _create_krita_document(self):
    '''Create the krita document'''
    image = self._render_page()  # Render the first page to the get the page size

    # Create a new krita document
    self.doc = Krita.instance().createDocument(image.width,
                                               image.height,
                                               'Krisenter',
                                               'RGBA',
                                               'U8',
                                               '',
                                               self.dpi)

    # Set the background image to the first page
    self.set_page(self.page_idx)

  def _render_page(self):
    '''Renders the page at self.page_idx'''
    page = self.pdf_document.create_page(self.page_idx)

    renderer = PageRenderer()
    renderer.set_render_hint(RenderHint.antialiasing,True)
    renderer.set_render_hint(RenderHint.text_antialiasing,True)
    image = renderer.render_page(page,
                                 xres=self.dpi,
                                 yres=self.dpi,
                                 )
    return image

  def set_page(self,
               page_idx):
    '''Set a page and return the width height and image data'''

#    # Keep the old overlay
#    if self.nodes is not None and self.doc is not None:
#      self.overlays[self.page_idx] = self.nodes[1].pixelData(0,0,self.doc.width(),self.doc.height())

    self.page_idx = page_idx

    image = self._render_page()

    # Get the current nodes (layers)
    root_node = self.doc.rootNode()
    nodes = root_node.childNodes()

    # Update the background image in position 0
    nodes[0].setPixelData(image.data,0,0,image.width,image.height)
    nodes[0].setOpacity(255)

    # Check if there is an overlay for the corresponding page otherwise
    # create one.
    if len(nodes)<self.page_idx+2:
      overlay_node = self.doc.createNode(f'Page {self.page_idx+1}', 'paintLayer')
      root_node.addChildNode(overlay_node, None)
      nodes = root_node.childNodes()

    # Make the new view visible
    for i,n in enumerate(nodes):
      n.setVisible( i in (0,self.page_idx+1) ) # Background and current page are visible
    self.doc.setActiveNode(nodes[self.page_idx+1])

    self.doc.refreshProjection()

  def get_doc(self):
    return self.doc

  def get_pdf_filename(self):
    return self.pdf_filename

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

  def close(self):
    '''Remove all layers and close the document'''

    # The following is an ugly way to not have to answer on whether we want to save
    # the file.

    root_node = self.doc.rootNode()
    nodes = root_node.childNodes()
    for node in nodes:
      node.remove()

    self.doc.setFileName(self.dummy_filename)
    self.doc.save()
    self.doc.close()
    self.doc.refreshProjection()
    os.unlink(self.dummy_filename)

  def error_dialog(self, message):
    QMessageBox.critical(self.qwindow,
                         'Error',
                         message)

# Here is the extension. It will install an instance of the
# PopplerNavigator into the krita python object.
class Krisenter(Extension):
  def __init__(self, parent):
    # This is initialising the parent, always important when subclassing.
    super().__init__(parent)
    self.qwindow = None

  def setup(self):
    pass

  def createActions(self, window):
    action_tool = window.createAction("kritaSlidyAction", "Krisenter", "tools/scripts")
    action_tool.triggered.connect(self.actionKrisenter)

    action_next = window.createAction('nextSlide',
                                      'Goto next slide',
                                      'tools/scripts')
    action_next.triggered.connect(self.gotoNextSlide)

    action_prev = window.createAction('prevSlide',
                                      'Goto prev slide',
                                      'tools/scripts')
    action_prev.triggered.connect(self.gotoPrevSlide)

    self.qwindow = window.qwindow() # Keep reference around for the messagebox

  def actionKrisenter(self):
    # Check if we have a running instance
    try:
      krita.krisenter_navigator
      if krita.krisenter_navigator is None:
        raise RuntimeError('No running krisenter')
      has_navigator = True
    except:
      has_navigator = False

    if has_navigator:
      kn = krita.krisenter_navigator
      dialog = KrisenterModifyDialog(kn.get_pdf_filename(),
                                     kn.get_doc())
      if dialog.exec_() == CLOSE_PRESENTATION:
        krita.krisenter_navigator.close()
        krita.krisenter_navigator = None
      dialog.close()
      return

    # TBDov: Remove this when done with debugging!
    if 0:
      filename = '/tmp/blue-circle.pdf'
    else:  
      krisenter_dialog = KrisenterNewPdfDialog()
      ret = krisenter_dialog.exec_()
  
      if ret==0: # Cancel - Is there an enum?
        return
  
      filename = krisenter_dialog.get_pdf_filename()

    if filename is None or not os.path.exists(filename):
      self.error_message('Need existing pdf file!')
      return

    krita.krisenter_navigator = PopplerNavigor(
      filename,
      qwindow=self.qwindow)

    doc = krita.krisenter_navigator.get_doc() # Get the new doc
    activeView = Krita.instance().activeWindow().activeView()
    Krita.instance().activeWindow().addView(doc)

  def error_message(self, message):
    QMessageBox.critical(self.qwindow,
                         'Error',
                         message)

  def gotoNextSlide(self):
    try:
      krita.krisenter_navigator.next_page()
    except:
      self.error_message('No krisenter pdfloaded!')
        

  def gotoPrevSlide(self):
    try:
      krita.krisenter_navigator.prev_page()
    except:
      self.error_message('No krisenter pdf loaded!')

# And add the extension to Krita's list of extensions:
Krita.instance().addExtension(Krisenter(Krita.instance()))
