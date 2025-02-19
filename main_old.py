import os
import sys
import cv2
import numpy as np
from PyQt5.QtCore import Qt, QRectF, QTimer
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QIntValidator
from PyQt5.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QPushButton,
                             QVBoxLayout, QWidget, QHBoxLayout, QInputDialog, QLineEdit, QLabel, QGroupBox, QFormLayout,
                             QMessageBox)

def detect_ticket_area(image):
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    # Definir una región de interés (ROI) en el centro de la imagen
    height, width = gray.shape
    roi = gray[0:int(height), 0:int(width)]

    # Aplicar el resto del proceso solo a la ROI
    blurred = cv2.GaussianBlur(roi, (5, 5), 0)
    edges = cv2.Canny(blurred, 100, 250)

    # Cerrar los contornos para unir líneas separadas
    kernel = np.ones((5, 5), np.uint8)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

#    cv2.imwrite("debug_edges.jpg", edges)
#    cv2.imwrite("debug_contours.jpg", closed)

    # Verificar si se encontraron contornos
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        valid_contours = []

        # Definir el porcentaje estimado para las áreas falsas en las esquinas
        width, height = image.shape[1], image.shape[0]
        margin_width = int(width * 0.45)  # 45% del ancho

        for contour in contours:
            # Obtener el rectángulo ajustado alrededor del contorno
            x, y, w, h = cv2.boundingRect(contour)

            # Excluir las áreas en las esquinas derechas (márgenes falsos)
            if x + w < width - margin_width:
                valid_contours.append((x, y, w, h))

        if valid_contours:
            # Obtener el rectángulo envolvente de todas las áreas válidas
            all_x = [x for x, y, w, h in valid_contours]
            all_y = [y for x, y, w, h in valid_contours]
            # all_w = [w for x, y, w, h in valid_contours]
            # all_h = [h for x, y, w, h in valid_contours]

            # Rectángulo envolvente
            min_x = min(all_x)
            min_y = min(all_y)
            max_x = max([x + w for x, y, w, h in valid_contours])
            max_y = max([y + h for x, y, w, h in valid_contours])

            # Ajustar el tamaño del área detectada
            adjusted_width = max_x - min_x
            adjusted_height = max_y - min_y

            return QRectF(min_x - 10, min_y - 10, adjusted_width + 10, adjusted_height + 10)

    else:
        print("No se detectaron contornos válidos.")
        return None


class ImageViewer(QGraphicsView):
    def __init__(self, parent=None, ticket_cropper=None):
        super().__init__(parent)
        self.ticket_cropper = ticket_cropper  # Guardamos la referencia a TicketCropper
        self.setDragMode(QGraphicsView.NoDrag)
        self.start_pos = None
        self.end_pos = None
        self.selection_rect = None
        self.rect_pen = QPen(QColor(255, 0, 0), 2, Qt.SolidLine)
        self.drawing = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.drawing = True
            self.selection_rect = None
            self.viewport().update()  # Forzar el refresco inmediato
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.end_pos = event.pos()
            self.viewport().update()  # Redibujar mientras arrastras el ratón
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            self.end_pos = event.pos()
            self.selection_rect = QRectF(self.start_pos, self.end_pos).normalized()
            self.update()

            # Activar el botón de recorte si la selección es válida
            if self.selection_rect.width() > 0 and self.selection_rect.height() > 0:
                self.ticket_cropper.crop_button.setEnabled(True)  # Usamos ticket_cropper aquí
            else:
                self.ticket_cropper.crop_button.setEnabled(False)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.drawing or (self.selection_rect and not self.selection_rect.isNull()):
            painter = QPainter(self.viewport())
            painter.setPen(self.rect_pen)
            rect = QRectF(self.start_pos, self.end_pos).normalized() if self.drawing else self.selection_rect
            painter.drawRect(rect)
            painter.end()  # Finalizar el pintor correctamente

    def get_selection_rect(self):
        if self.selection_rect and not self.selection_rect.isNull():
            # Devuelve directamente las coordenadas de selección sin mapear a escena
            return QRectF(self.mapToScene(self.selection_rect.topLeft().toPoint()),
                          self.mapToScene(self.selection_rect.bottomRight().toPoint()))
        return None

    def clear_selection(self):
        self.selection_rect = None
        self.viewport().update()  # Asegurarse de que desaparezca visualmente
        # Desactivar el botón de recorte si la selección es borrada


#        self.ticket_cropper.crop_button.setEnabled(False)


class TicketCropper(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_dir = 'C:/temp/cosas/misdocs/varios/escaneos/tickets/todo'
        self.save_dir = 'C:/temp/cosas/misdocs/varios/escaneos/tickets/done'
        self.image_files = [f for f in os.listdir(self.image_dir) if f.lower().endswith(('png', 'jpg', 'jpeg'))]
        self.current_index = 0
        self.jpeg_quality = 90  # Valor inicial de la calidad JPEG
        self.init_ui()
        self.load_image()

    def init_ui(self):
        self.setWindowTitle('Ticket Cropper')
        self.resize(800, 600)

        main_layout = QVBoxLayout()

        # Parte para mostrar la imagen
        self.scene = QGraphicsScene(self)
        self.image_view = ImageViewer(self, ticket_cropper=self)
        self.image_view.setScene(self.scene)
        main_layout.addWidget(self.image_view)

        # Barra de controles: Añadir etiqueta y entrada de calidad JPEG y nombre del archivo
        control_layout = QVBoxLayout()

        # Crear un grupo para los controles
        controls_group = QGroupBox("Image Controls", self)
        controls_layout = QFormLayout(controls_group)  # Usamos QFormLayout para alinear etiquetas y campos

        # 'File Name' label en la parte superior
        self.file_name_label = QLabel('Archivo: ', self)
        control_layout.addWidget(self.file_name_label)

        # 'JPEG Quality' label y entrada
        self.quality_label = QLabel('JPEG Quality:', self)
        self.quality_input = QLineEdit(str(self.jpeg_quality), self)
        self.quality_input.setValidator(QIntValidator(1, 100))  # Validar que el valor esté entre 1 y 100
        self.quality_input.setPlaceholderText("1-100")
        self.quality_input.setFixedWidth(80)  # Limitar el ancho del campo de calidad
        self.quality_input.textChanged.connect(self.update_quality)
        controls_layout.addRow(self.quality_label, self.quality_input)

        # 'File Cropped Name' label y entrada
        self.filename_label = QLabel('File Cropped Name:', self)
        self.custom_filename_input = QLineEdit(self)
        self.custom_filename_input.setPlaceholderText("Enter file name")
        self.custom_filename_input.setFixedWidth(250)  # Limitar el ancho del campo de nombre
        self.custom_filename_input.returnPressed.connect(self.crop_and_save)
        controls_layout.addRow(self.filename_label, self.custom_filename_input)

        # Añadir el grupo de controles al layout principal
        control_layout.addWidget(controls_group)

        # Barra de botones
        button_layout = QHBoxLayout()
        self.prev_button = QPushButton('Anterior')
        self.prev_button.clicked.connect(self.prev_image)
        button_layout.addWidget(self.prev_button)

        self.next_button = QPushButton('Siguiente')
        self.next_button.clicked.connect(self.next_image)
        button_layout.addWidget(self.next_button)

        self.crop_button = QPushButton('Recortar y Guardar')
        self.crop_button.clicked.connect(self.crop_and_save)
        #        self.crop_button.setEnabled(False)
        button_layout.addWidget(self.crop_button)

        self.exit_button = QPushButton('Salir')
        self.exit_button.clicked.connect(self.close)
        button_layout.addWidget(self.exit_button)

        main_layout.addLayout(control_layout)  # Añadir la fila de controles
        main_layout.addLayout(button_layout)  # Añadir la barra de botones

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Abrir la ventana maximizada
        self.showMaximized()

    def load_image(self):
        if 0 <= self.current_index < len(self.image_files):
            image_path = os.path.join(self.image_dir, self.image_files[self.current_index])
            image = cv2.imread(image_path)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            height, width, channel = image.shape
            bytes_per_line = 3 * width
            qimage = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimage)

            self.scene.clear()
            self.pixmap_item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.pixmap_item)
            self.image_view.setScene(self.scene)

            # Ajustar la imagen para que se centre en la vista
            QTimer.singleShot(50, lambda: self.image_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio))

            # # Después de aplicar fitInView, puedes llamar a update_selection_area para ajustar el área seleccionada:
            # self.update_selection_area()

            # Limpiar cualquier zona marcada de la imagen anterior
            self.image_view.selection_rect = None
            self.image_view.viewport().update()  # Forzar la actualización

            QTimer.singleShot(100, lambda: self.mark_detected_area(image))

            # Actualizar el label con el nombre del archivo
            self.file_name_label.setText(f'Archivo: {self.image_files[self.current_index]}')
            self.custom_filename_input.setText("")

    def mark_detected_area(self, image):
        auto_rect = detect_ticket_area(image)
        if auto_rect:
            transform = self.image_view.transform()
            scale_x = transform.m11()
            scale_y = transform.m22()

            scaled_width = self.pixmap_item.pixmap().width() * scale_x
            scaled_height = self.pixmap_item.pixmap().height() * scale_y

            view_width = self.image_view.viewport().width()
            view_height = self.image_view.viewport().height()

            offset_x = max((view_width - scaled_width) / 2, 0)
            offset_y = max((view_height - scaled_height) / 2, 0)

            adjusted_left = auto_rect.left() * scale_x + offset_x
            adjusted_top = auto_rect.top() * scale_y + offset_y
            adjusted_width = auto_rect.width() * scale_x
            adjusted_height = auto_rect.height() * scale_y

            adjusted_rect = QRectF(adjusted_left, adjusted_top, adjusted_width, adjusted_height)

            self.image_view.selection_rect = adjusted_rect
            self.image_view.viewport().update()
        else:
            print("No se detectó ninguna zona automáticamente.")

    def crop_and_save(self):
        """
        Recorta y guarda la imagen utilizando la región detectada automáticamente o la selección manual.
        """
        image_path = os.path.join(self.image_dir, self.image_files[self.current_index])
        image = cv2.imread(image_path)

        # Usar siempre la selección (manual o automática) para recortar
        selection_rect = self.image_view.get_selection_rect()

        if selection_rect is None:
            return

        # Convertir la selección a las coordenadas de la imagen original
        height, width = image.shape[:2]
        x1 = max(0, int(selection_rect.left() * width / self.pixmap_item.pixmap().width()))
        y1 = max(0, int(selection_rect.top() * height / self.pixmap_item.pixmap().height()))
        x2 = min(width, int(selection_rect.right() * width / self.pixmap_item.pixmap().width()))
        y2 = min(height, int(selection_rect.bottom() * height / self.pixmap_item.pixmap().height()))

        if x1 >= x2 or y1 >= y2:
            return

        cropped_image = image[y1:y2, x1:x2]

        # Obtener el nombre del archivo desde el campo de texto
        custom_filename = self.custom_filename_input.text().strip()
        if not custom_filename:
            custom_filename, ok = QInputDialog.getText(self, 'Guardar recorte',
                                                       'Introduce el nombre del archivo (sin extensión):')
            if not ok or not custom_filename:
                return

        # Obtener la calidad JPEG desde el campo de texto
        quality = self.jpeg_quality
        try:
            quality = int(self.quality_input.text())
        except ValueError:
            quality = self.jpeg_quality  # Usar el valor predeterminado si no es válido

        save_path = os.path.join(self.save_dir, f"{custom_filename}.jpg")

        if os.path.exists(save_path):
            QMessageBox.warning(self, "Error", "El archivo ya existe. Elija otro nombre.")
            return

        cv2.imwrite(save_path, cropped_image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])

        self.next_image()  # Avanzar automáticamente a la siguiente imagen después de guardar

    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_image()

    def next_image(self):
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.load_image()

    def update_quality(self):
        try:
            self.jpeg_quality = int(self.quality_input.text())
        except ValueError:
            pass  # Si el valor no es válido, mantenemos el valor anterior


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TicketCropper()
    window.show()  # Esto se puede eliminar, ya que showMaximized lo hará
    sys.exit(app.exec_())
