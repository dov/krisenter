import krita
from krita import *

class NextSlide(Extension):

    def __init__(self, parent):
      # This is initialising the parent, always important when subclassing.
      super().__init__(parent)

    def setup(self):
      pass

    def createActions(self, window):
      action = window.createAction('nextSlide',
                                   'Goto next slide',
                                   'tools/scripts')
      action.triggered.connect(self.gotoNextSlide)
      self.qwindow = window.qwindow() 

    def gotoNextSlide(self):
      try:
        krita.krisenter_navigator.next_page()
      except:
        QMessageBox.critical(self.qwindow,
                            'Error',
                             'No krisenter show loaded!')
        
        

# And add the extension to Krita's list of extensions:
Krita.instance().addExtension(NextSlide(Krita.instance()))
