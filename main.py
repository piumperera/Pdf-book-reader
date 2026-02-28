import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QFileDialog, 
                             QVBoxLayout, QWidget, QToolBar, QMessageBox, QLabel)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from pdf_view import PDFView

class PDFReaderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Book Reader")
        self.resize(1000, 800)
        self.initUI()
        
    def initUI(self):
        # Apply modern styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QToolBar {
                background-color: #3c3f41;
                border: none;
                spacing: 10px;
                padding: 10px;
            }
            QToolBar QToolButton {
                color: #ffffff;
                background-color: #4CAF50;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QToolBar QToolButton:hover {
                background-color: #45a049;
            }
            QScrollBar:vertical {
                border: none;
                background: #2b2b2b;
                width: 14px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 7px;
                margin: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QGraphicsView {
                border: none;
                background-color: #1e1e1e;
            }
            QLabel#page_label {
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                padding: 0 10px;
            }
        """)

        # Main Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Toolbar
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        # Open Action
        open_action = QAction("Open PDF", self)
        open_action.setStatusTip("Open a PDF document")
        open_action.triggered.connect(self.open_pdf)
        self.toolbar.addAction(open_action)

        # Close File Action
        close_action = QAction("Close File", self)
        close_action.setStatusTip("Close the current PDF")
        close_action.triggered.connect(self.close_pdf)
        self.toolbar.addAction(close_action)

        # Navigation Actions
        prev_action = QAction("Previous Page", self)
        prev_action.triggered.connect(self.prev_page)
        self.toolbar.addAction(prev_action)
        
        next_action = QAction("Next Page", self)
        next_action.triggered.connect(self.next_page)
        self.toolbar.addAction(next_action)

        # Zoom Actions
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        self.toolbar.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        self.toolbar.addAction(zoom_out_action)
        
        fit_width_action = QAction("Fit Width", self)
        fit_width_action.triggered.connect(self.fit_width)
        self.toolbar.addAction(fit_width_action)
        
        # Full Screen Action
        fullscreen_action = QAction("Full Screen", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.setStatusTip("Toggle Full Screen (F11)")
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        self.toolbar.addAction(fullscreen_action)
        
        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().Policy.Expanding, spacer.sizePolicy().Policy.Preferred)
        self.toolbar.addWidget(spacer)

        # Page Display
        self.page_label = QLabel("- / -")
        self.page_label.setObjectName("page_label")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.toolbar.addWidget(self.page_label)


        # PDF View
        self.pdf_view = PDFView(self)
        self.pdf_view.page_changed.connect(self.update_page_label)
        self.layout.addWidget(self.pdf_view)

    def update_page_label(self, current, total):
        if total > 0:
            # Display is 1-indexed for the user
            self.page_label.setText(f"Page {current + 1} / {total}")
        else:
            self.page_label.setText("- / -")

    def open_pdf(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF Document",
            "",
            "PDF Files (*.pdf);;All Files (*)"
        )
        if file_name:
            try:
                self.pdf_view.load_pdf(file_name)
                self.setWindowTitle(f"PDF Book Reader - {file_name}")
            except Exception as e:
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Error Loading PDF", f"Could not load the selected PDF.\n\n{str(e)}")

    def close_pdf(self):
        self.pdf_view.load_pdf(None)
        self.setWindowTitle("PDF Book Reader")
        
    def prev_page(self):
        if self.pdf_view.doc:
            if self.pdf_view.current_page_idx > 0:
                self.pdf_view.current_page_idx -= 1
                self.pdf_view.display_page()
                
    def next_page(self):
        if self.pdf_view.doc:
            if self.pdf_view.current_page_idx < len(self.pdf_view.doc) - 1:
                self.pdf_view.current_page_idx += 1
                self.pdf_view.display_page()

    def zoom_in(self):
        self.pdf_view.zoom_in()
        
    def zoom_out(self):
        self.pdf_view.zoom_out()

    def fit_width(self):
        self.pdf_view.fit_to_width()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFReaderWindow()
    window.show()
    sys.exit(app.exec())
