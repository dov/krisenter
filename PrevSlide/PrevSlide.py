import krita
from krita import *

class PrevSlide(Extension):

    def __init__(self, parent):
      # This is initialising the parent, always important when subclassing.
      super().__init__(parent)

    def setup(self):
      pass

    def createActions(self, window):
      action = window.createAction('prevSlide',
                                   'Goto previous slide',
                                   'tools/scripts')
      action.triggered.connect(self.gotoPrevSlide)
      self.qwindow = window.qwindow() 

    def gotoPrevSlide(self):
      try:
        krita.krisenter_navigator.prev_page()
      except:
        QMessageBox.critical(self.qwindow,
                            'Error',
                             'No krisenter show loaded!')

# And add the extension to Krita's list of extensions:
Krita.instance().addExtension(PrevSlide(Krita.instance()))
