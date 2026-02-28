import fitz  # PyMuPDF
from PyQt6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, 
                             QGraphicsRectItem)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt, QRectF, pyqtSignal

class SentenceHighlightItem:
    def __init__(self, rects, text):
        self.rects = rects  # list of fitz.Rect
        self.text = text
        self.visual_items = []

class PDFView(QGraphicsView):
    page_changed = pyqtSignal(int, int) # current_index, total_pages

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter) # Center perfectly in viewport
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse) # Zoom anchors to mouse pointer
        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        
        # State
        self.doc = None
        self.current_page_idx = 0
        self.page_item = None
        
        self.sentences = []
        self.hovered_sentence = None
        self.locked_sentence = None
        self.locked_sentence_idx = -1
        self.hovered_visual_items = []
        self.locked_visual_items = []
        self.zoom_factor = 1.0  # Viewport hardware zoom level
        self.render_scale = 4.0 # Base image ultra-high-res internal rendering scale

    def load_pdf(self, file_path):
        if self.doc:
            self.doc.close()
            self.doc = None

        if file_path:
            self.doc = fitz.open(file_path)
            self.current_page_idx = 0
            self.display_page()
            self.fit_to_width()
            self.page_changed.emit(self.current_page_idx, len(self.doc))
        else:
            self.scene().clear()
            self.sentences = []
            self.hovered_sentence = None
            self.locked_sentence = None
            self.locked_sentence_idx = -1
            self.hovered_visual_items = []
            self.locked_visual_items = []
            self.page_changed.emit(0, 0)

    def display_page(self):
        self.scene().clear()
        self.sentences = []
        self.hovered_sentence = None
        self.locked_sentence = None
        self.locked_sentence_idx = -1
        self.hovered_visual_items = []
        self.locked_visual_items = []
        
        if not self.doc or self.current_page_idx >= len(self.doc):
            return

        page = self.doc.load_page(self.current_page_idx)
        
        # Render the PDF image at fixed ultra-high resolution
        mat = fitz.Matrix(self.render_scale, self.render_scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        from PyQt6.QtGui import QImage, QPixmap
        fmt = QImage.Format.Format_RGB888
        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
        # Setting device ratio ensures scene coords match the document's native points!
        qimg.setDevicePixelRatio(self.render_scale) 
        qpixmap = QPixmap.fromImage(qimg)
        
        self.page_item = QGraphicsPixmapItem(qpixmap)
        self.page_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.scene().addItem(self.page_item)
        
        # Add a margin around the document page for centering aesthetics
        rect = self.page_item.pixmap().rect()
        margin = 40
        self.setSceneRect(QRectF(-margin, -margin, rect.width() + 2 * margin, rect.height() + 2 * margin))

        self.extract_sentences(page)
        self._apply_zoom()

    def extract_sentences(self, page):
        words = page.get_text("words")
        words.sort(key=lambda w: (w[5], w[6], w[0]))

        current_sentence_rects = []
        current_sentence_text = []
        terminators = ('.', '?', '!')

        for w in words:
            x0, y0, x1, y1 = w[0], w[1], w[2], w[3]
            word_text = w[4]
            current_sentence_rects.append(fitz.Rect(x0, y0, x1, y1))
            current_sentence_text.append(word_text)
            
            if any(word_text.endswith(term) for term in terminators) or any(word_text.endswith(term + '"') for term in terminators) or any(word_text.endswith(term + "'") for term in terminators):
                self.sentences.append(SentenceHighlightItem(
                    list(current_sentence_rects),
                    " ".join(current_sentence_text)
                ))
                current_sentence_rects.clear()
                current_sentence_text.clear()

        if current_sentence_rects:
            self.sentences.append(SentenceHighlightItem(
                list(current_sentence_rects),
                " ".join(current_sentence_text)
            ))

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        
        if not self.sentences:
            return
            
        scene_pos = self.mapToScene(event.pos())
        spos_x, spos_y = scene_pos.x(), scene_pos.y()
        
        found_sentence = None
        for sentence in self.sentences:
            for r in sentence.rects:
                if r.x0 <= spos_x <= r.x1 and r.y0 <= spos_y <= r.y1:
                    found_sentence = sentence
                    break
            if found_sentence:
                break
        
        if found_sentence != self.hovered_sentence:
            self.hovered_sentence = found_sentence
            self._update_all_highlights()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            spos_x, spos_y = scene_pos.x(), scene_pos.y()
            
            found_idx = -1
            for i, sentence in enumerate(self.sentences):
                for r in sentence.rects:
                    if r.x0 <= spos_x <= r.x1 and r.y0 <= spos_y <= r.y1:
                        found_idx = i
                        break
                if found_idx != -1:
                    break
            
            if found_idx != -1:
                self.locked_sentence_idx = found_idx
                self.locked_sentence = self.sentences[found_idx]
                self._update_all_highlights()
                
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Left:
            if self.doc and self.current_page_idx > 0:
                self.current_page_idx -= 1
                self.display_page()
                self.page_changed.emit(self.current_page_idx, len(self.doc))
            return
        elif event.key() == Qt.Key.Key_Right:
            if self.doc and self.current_page_idx < len(self.doc) - 1:
                self.current_page_idx += 1
                self.display_page()
                self.page_changed.emit(self.current_page_idx, len(self.doc))
            return

        if not self.sentences:
            super().keyPressEvent(event)
            return
            
        if event.key() == Qt.Key.Key_Down:
            if self.locked_sentence_idx == -1:
                self.locked_sentence_idx = 0
            elif self.locked_sentence_idx < len(self.sentences) - 1:
                self.locked_sentence_idx += 1
            self.locked_sentence = self.sentences[self.locked_sentence_idx]
            self._update_all_highlights()
            self._scroll_to_sentence(self.locked_sentence)
            
        elif event.key() == Qt.Key.Key_Up:
            if self.locked_sentence_idx == -1:
                self.locked_sentence_idx = len(self.sentences) - 1
            elif self.locked_sentence_idx > 0:
                self.locked_sentence_idx -= 1
            self.locked_sentence = self.sentences[self.locked_sentence_idx]
            self._update_all_highlights()
            self._scroll_to_sentence(self.locked_sentence)
        else:
            super().keyPressEvent(event)

    def _scroll_to_sentence(self, sentence):
        if sentence and sentence.rects:
            # Ensure the sentence is visible
            first_rect = sentence.rects[0]
            # Create a combined bounding box to fit the entire sentence
            combined = fitz.Rect(first_rect)
            for r in sentence.rects[1:]:
                combined = combined | r
                
            qrect = QRectF(combined.x0, combined.y0, combined.x1 - combined.x0, combined.y1 - combined.y0)
            self.ensureVisible(qrect, 50, 50)

    def _update_all_highlights(self):
        # Clear existing highlights
        for item in self.hovered_visual_items + self.locked_visual_items:
            self.scene().removeItem(item)
        self.hovered_visual_items.clear()
        self.locked_visual_items.clear()
        
        from PyQt6.QtGui import QColor, QBrush, QPen
        pen = QPen(Qt.PenStyle.NoPen)
        
        # Draw locked highlight (e.g. permanent light blue)
        if self.locked_sentence:
            highlight_color = QColor(255, 255, 0, 100)
            brush = QBrush(highlight_color)
            merged_rects = self._merge_rects(self.locked_sentence.rects)
            for r in merged_rects:
                padding = 2.0
                qrect = QRectF(r.x0 - padding, r.y0 - padding, 
                               (r.x1 - r.x0) + 2*padding, (r.y1 - r.y0) + 2*padding)
                rect_item = self.scene().addRect(qrect, pen, brush)
                self.locked_visual_items.append(rect_item)
                
        # Draw hovered highlight (e.g. yellow) only if it's different from the locked sentence
        if self.hovered_sentence and self.hovered_sentence != self.locked_sentence:
            highlight_color = QColor(255, 255, 0, 100)
            brush = QBrush(highlight_color)
            merged_rects = self._merge_rects(self.hovered_sentence.rects)
            for r in merged_rects:
                padding = 2.0
                qrect = QRectF(r.x0 - padding, r.y0 - padding, 
                               (r.x1 - r.x0) + 2*padding, (r.y1 - r.y0) + 2*padding)
                rect_item = self.scene().addRect(qrect, pen, brush)
                self.hovered_visual_items.append(rect_item)

    def _merge_rects(self, rects):
        if not rects:
            return []
            
        merged = []
        current = fitz.Rect(rects[0])
        
        for r in rects[1:]:
            if abs(current.y0 - r.y0) < 5 and abs(current.y1 - r.y1) < 5:
                current = current | r
            else:
                merged.append(current)
                current = fitz.Rect(r)
                
        merged.append(current)
        return merged

    def _apply_zoom(self):
        from PyQt6.QtGui import QTransform
        self.setTransform(QTransform().scale(self.zoom_factor, self.zoom_factor))

    def zoom_in(self):
        if self.doc and self.zoom_factor < 10.0:
            self.zoom_factor += 0.2
            self._apply_zoom()
            
    def zoom_out(self):
        if self.doc and self.zoom_factor > 0.2:
            self.zoom_factor -= 0.2
            self._apply_zoom()

    def fit_to_width(self):
        if not self.doc:
            return
            
        view_width = self.viewport().width()
        page = self.doc.load_page(self.current_page_idx)
        page_width = page.rect.width
        
        desired_width = view_width - 100 
        if desired_width < 100: desired_width = 100
        
        self.zoom_factor = desired_width / page_width
        self._apply_zoom()

    def wheelEvent(self, event):
        modifiers = event.modifiers()
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            zoom_step = delta / 1200.0  # Gives a nice smooth step logic
            new_zoom = self.zoom_factor + zoom_step
            
            if new_zoom < 0.1: new_zoom = 0.1
            if new_zoom > 10.0: new_zoom = 10.0
            
            self.zoom_factor = new_zoom
            self._apply_zoom()
            event.accept()
        else:
            super().wheelEvent(event)
