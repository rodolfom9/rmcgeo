"""
/***************************************************************************
 RMCGeo
                                 A QGIS plugin
 Conjunto de ferramentas para simplificar tarefas geoespaciais.
                             -------------------
        begin                : 2025-10-26
        copyright            : (C) 2025 by Rodolfo Martins de Carvalho
        email                : rodolfomartins09@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import math
from qgis.core import (
    Qgis, QgsWkbTypes, QgsGeometry, QgsPointXY,
    QgsVectorLayer, QgsRectangle, QgsFeatureRequest, QgsMapLayerType,
    QgsCoordinateTransform, QgsProject
)
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QMessageBox


class ChanfroTool(QgsMapTool):
    """Ferramenta Chanfro - Estende duas linhas até que se encontrem."""
    
    def __init__(self, canvas, iface):
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        self.first_line = None
        self.second_line = None
        self.step = 0
        
        self.search_radius = 10
        self.hover_feature = None
        self.hover_layer = None
        
        try:
            self.setCursor(Qt.CursorShape.CrossCursor)  # Qt6
        except AttributeError:
            self.setCursor(Qt.CrossCursor)  # Qt5
        
        self.hover_rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.hover_rubber_band.setColor(QColor(255, 0, 0, 180))
        self.hover_rubber_band.setWidth(3)
        
        self.first_rubber_band = self.create_rubber_band(
            QgsWkbTypes.LineGeometry, QColor(0, 255, 0, 180), 3
        )
        self.second_rubber_band = self.create_rubber_band(
            QgsWkbTypes.LineGeometry, QColor(255, 255, 0, 180), 3
        )
        
        self.preview_rubber_band = self.create_rubber_band(
            QgsWkbTypes.LineGeometry, QColor(0, 150, 255, 150), 2
        )
        
        self.intersection_rubber_band = self.create_rubber_band(
            QgsWkbTypes.PointGeometry, QColor(255, 0, 0, 200), 5
        )

    def activate(self):
        super().activate()
        # Verifica se a camada ativa é uma camada de linha
        active_layer = self.iface.activeLayer()
        if not active_layer or active_layer.type() != QgsMapLayerType.VectorLayer or \
           active_layer.geometryType() != QgsWkbTypes.LineGeometry:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Camada Inválida",
                "Por favor, selecione uma camada de linhas para trabalhar com a ferramenta Chanfro."
            )
            # Desativa a ferramenta se a camada não for adequada
            self.canvas.unsetMapTool(self)
            return
        
    def canvasMoveEvent(self, event):
        point = self.toMapCoordinates(event.pos())
        self.update_hover_highlight(point)
        
        if self.step == 1 and self.first_line and self.hover_feature:
            if self.hover_feature.id() != self.first_line.id():
                self.create_chamfer_preview(
                    self.first_line.geometry(),
                    self.hover_feature.geometry()
                )
    
    def canvasPressEvent(self, event):
        try:
            right_button = Qt.MouseButton.RightButton  # Qt6
            left_button = Qt.MouseButton.LeftButton  # Qt6
        except AttributeError:
            right_button = Qt.RightButton  # Qt5
            left_button = Qt.LeftButton  # Qt5
        
        # Botão direito cancela a operação (não processa)
        if event.button() == right_button:
            return
        
        # Apenas processa clique esquerdo
        if event.button() != left_button:
            return
        
        layer = self.get_active_layer()
        if not layer:
            return
        
        if not self.is_line_layer(layer):
            return
        
        if not self.ensure_edit_mode(layer):
            return
        
        if not self.hover_feature or not self.hover_layer:
            return
        
        closest_feature = self.hover_feature
        
        if self.step == 0:
            self.first_line = closest_feature
            self.step = 1
            self.first_rubber_band.reset(QgsWkbTypes.LineGeometry)
            self.first_rubber_band.setToGeometry(closest_feature.geometry(), layer)
            
        elif self.step == 1:
            self.second_line = closest_feature
            
            self.second_rubber_band.reset(QgsWkbTypes.LineGeometry)
            self.second_rubber_band.setToGeometry(closest_feature.geometry(), layer)
            
            self.perform_chanfro(layer)
            
            self.reset_tool()
    
    def perform_chanfro(self, layer):
        """Executa a operação de chanfro (estende as linhas até se encontrarem)."""
        if not self.first_line or not self.second_line:
            return
        
        first_geom = self.first_line.geometry()
        second_geom = self.second_line.geometry()
        
        if not first_geom or not second_geom:
            return
        
        if self.first_line.id() == self.second_line.id():
            return
        
        is_valid, intersection_point, error_message = self.validate_chamfer(first_geom, second_geom)
        
        if not is_valid:
            return
        
        extended_first = self.extend_line_to_point(first_geom, intersection_point)
        extended_second = self.extend_line_to_point(second_geom, intersection_point)
        
        if not extended_first or not extended_second:
            self.show_message(
                "Erro ao estender as linhas!",
                Qgis.Critical
            )
            return
        
        success1 = self.update_feature_geometry(layer, self.first_line, extended_first)
        success2 = self.update_feature_geometry(layer, self.second_line, extended_second)
    
    def create_chamfer_preview(self, geom1, geom2):
        """Cria um preview visual do chanfro mostrando as extensões e o ponto de interseção."""
        # Limpa previews anteriores
        self.preview_rubber_band.reset()
        self.intersection_rubber_band.reset()
        
        # Valida o chanfro
        is_valid, intersection_point, _ = self.validate_chamfer(geom1, geom2)
        
        if not is_valid or not intersection_point:
            return
        
        extended_first = self.extend_line_to_point(geom1, intersection_point)
        extended_second = self.extend_line_to_point(geom2, intersection_point)
        
        if extended_first and extended_second:
            extended_first_canvas = self.transform_geometry_to_canvas_crs(extended_first, self.first_line and self.hover_layer)
            extended_second_canvas = self.transform_geometry_to_canvas_crs(extended_second, self.hover_layer)
            
            self.preview_rubber_band.reset(QgsWkbTypes.LineGeometry)
            self.preview_rubber_band.addGeometry(extended_first_canvas)
            self.preview_rubber_band.addGeometry(extended_second_canvas)
            
            point_geom = QgsGeometry.fromPointXY(intersection_point)
            point_geom_canvas = self.transform_geometry_to_canvas_crs(point_geom, self.hover_layer)
            
            self.intersection_rubber_band.reset(QgsWkbTypes.PointGeometry)
            self.intersection_rubber_band.addGeometry(point_geom_canvas)
    
    def _get_line_points(self, geom):
        """Extrai pontos de uma geometria de linha (multipart ou simples)."""
        return geom.asMultiPolyline()[0] if geom.isMultipart() else geom.asPolyline()
    
    def calculate_angle_between_lines(self, geom1, geom2, intersection_point):
        """Calcula o ângulo entre duas linhas considerando suas extremidades
        mais próximas do ponto de interseção."""
        points1 = self._get_line_points(geom1)
        points2 = self._get_line_points(geom2)
        
        if len(points1) < 2 or len(points2) < 2:
            return None, None, None, None, None
        
        # Determina qual extremidade de cada linha está mais próxima da interseção
        first1 = points1[0]
        last1 = points1[-1]
        first2 = points2[0]
        last2 = points2[-1]
        
        dist_to_first1 = first1.distance(intersection_point)
        dist_to_last1 = last1.distance(intersection_point)
        dist_to_first2 = first2.distance(intersection_point)
        dist_to_last2 = last2.distance(intersection_point)
        
        if dist_to_last1 < dist_to_first1:
            p1_start = points1[-2] if len(points1) > 1 else points1[0]
            p1_end = points1[-1]
        else:
            p1_end = points1[0]
            p1_start = points1[1] if len(points1) > 1 else points1[-1]
        
        if dist_to_last2 < dist_to_first2:
            p2_start = points2[-2] if len(points2) > 1 else points2[0]
            p2_end = points2[-1]
        else:
            p2_end = points2[0]
            p2_start = points2[1] if len(points2) > 1 else points2[-1]
        
        dx1 = p1_end.x() - p1_start.x()
        dy1 = p1_end.y() - p1_start.y()
        
        dx2 = p2_end.x() - p2_start.x()
        dy2 = p2_end.y() - p2_start.y()
        
        mag1 = math.sqrt(dx1 * dx1 + dy1 * dy1)
        mag2 = math.sqrt(dx2 * dx2 + dy2 * dy2)
        
        if mag1 == 0 or mag2 == 0:
            return None, None, None, None, None
        
        dx1_norm = dx1 / mag1
        dy1_norm = dy1 / mag1
        dx2_norm = dx2 / mag2
        dy2_norm = dy2 / mag2
        
        dot_product = dx1_norm * dx2_norm + dy1_norm * dy2_norm
        
        dot_product = max(-1.0, min(1.0, dot_product))
        
        angle_rad = math.acos(abs(dot_product))
        angle_deg = math.degrees(angle_rad)
        
        return angle_deg, p1_start, p1_end, p2_start, p2_end
    
    def validate_chamfer(self, geom1, geom2):
        """Valida se o chanfro pode ser executado.
        O chanfro é válido apenas se a interseção ocorrer além das extremidades das linhas."""
        if not geom1 or not geom2:
            return False, None, "Geometrias inválidas"
        
        points1 = self._get_line_points(geom1)
        points2 = self._get_line_points(geom2)
        
        if len(points1) < 2 or len(points2) < 2:
            return False, None, "Linhas com poucos pontos"
        
        if geom1.intersects(geom2):
            intersection = geom1.intersection(geom2)
            if not intersection.isEmpty():
                return False, None, "As linhas já se intersectam"
        
        intersection_point = self.find_extended_intersection(geom1, geom2)
        
        if not intersection_point:
            return False, None, "Linhas paralelas ou sem interseção válida"
        
        angle_result = self.calculate_angle_between_lines(geom1, geom2, intersection_point)
        
        if angle_result[0] is None:
            return False, None, "Erro ao calcular o ângulo entre as linhas"
        
        angle_deg, p1_start, p1_end, p2_start, p2_end = angle_result
        
        MIN_ANGLE_DEGREES = 5.0
        
        if angle_deg < MIN_ANGLE_DEGREES:
            return False, None, f"As linhas são quase paralelas (ângulo: {angle_deg:.1f}°).\nO chanfro seria desproporcional.\nÂngulo mínimo: {MIN_ANGLE_DEGREES}°"
        
        first1 = points1[0]
        last1 = points1[-1]
        first2 = points2[0]
        last2 = points2[-1]
        
        dist_to_first1 = first1.distance(intersection_point)
        dist_to_last1 = last1.distance(intersection_point)
        dist_to_first2 = first2.distance(intersection_point)
        dist_to_last2 = last2.distance(intersection_point)
        
        line1_length = geom1.length()
        tolerance = line1_length * 0.01
        
        if abs((dist_to_first1 + dist_to_last1) - line1_length) < tolerance:
            return False, None, "A interseção está no meio da primeira linha.\nO chanfro só pode ser criado nas extremidades."
        
        line2_length = geom2.length()
        tolerance2 = line2_length * 0.01
        
        if abs((dist_to_first2 + dist_to_last2) - line2_length) < tolerance2:
            return False, None, "A interseção está no meio da segunda linha.\nO chanfro só pode ser criado nas extremidades."
        
        dx1 = p1_end.x() - p1_start.x()
        dy1 = p1_end.y() - p1_start.y()
        
        dx2 = p2_end.x() - p2_start.x()
        dy2 = p2_end.y() - p2_start.y()
        
        dx1_int = intersection_point.x() - p1_end.x()
        dy1_int = intersection_point.y() - p1_end.y()
        
        dot1 = dx1 * dx1_int + dy1 * dy1_int
        
        dx2_int = intersection_point.x() - p2_end.x()
        dy2_int = intersection_point.y() - p2_end.y()
        
        dot2 = dx2 * dx2_int + dy2 * dy2_int
        
        min_dot_threshold = -line1_length * 0.1
        
        if dot1 < min_dot_threshold and dot2 < min_dot_threshold:
            return False, None, "A interseção está na direção oposta.\nAs linhas não convergem."
        
        return True, intersection_point, ""
    
    def find_extended_intersection(self, geom1, geom2):
        points1 = self._get_line_points(geom1)
        points2 = self._get_line_points(geom2)
        
        if len(points1) < 2 or len(points2) < 2:
            return None
        
        combinations = [
            ((points1[-2], points1[-1]), (points2[-2], points2[-1])),
            ((points1[-2], points1[-1]), (points2[1], points2[0])),
            ((points1[1], points1[0]), (points2[-2], points2[-1])),
            ((points1[1], points1[0]), (points2[1], points2[0]))
        ]
        
        valid_intersections = []
        
        for (p1_start, p1_end), (p2_start, p2_end) in combinations:
            # Calcula os vetores de direção
            dx1 = p1_end.x() - p1_start.x()
            dy1 = p1_end.y() - p1_start.y()
            
            dx2 = p2_end.x() - p2_start.x()
            dy2 = p2_end.y() - p2_start.y()
            
            cross = dx1 * dy2 - dy1 * dx2
            
            if abs(cross) < 1e-10:
                continue
            
            dx = p2_end.x() - p1_end.x()
            dy = p2_end.y() - p1_end.y()
            
            t1 = (dx * dy2 - dy * dx2) / cross
            t2 = (dx * dy1 - dy * dx1) / cross
            
            intersection_x = p1_end.x() + t1 * dx1
            intersection_y = p1_end.y() + t1 * dy1
            intersection_point = QgsPointXY(intersection_x, intersection_y)
            
            if t1 >= -0.01 and t2 >= -0.01:
                dist_sum = p1_end.distance(intersection_point) + p2_end.distance(intersection_point)
                valid_intersections.append((intersection_point, dist_sum, t1, t2))
        
        if not valid_intersections:
            # Se nenhuma interseção válida, retorna a primeira calculada (compatibilidade)
            p1_start = points1[-2]
            p1_end = points1[-1]
            p2_start = points2[-2]
            p2_end = points2[-1]
            
            dx1 = p1_end.x() - p1_start.x()
            dy1 = p1_end.y() - p1_start.y()
            dx2 = p2_end.x() - p2_start.x()
            dy2 = p2_end.y() - p2_start.y()
            
            cross = dx1 * dy2 - dy1 * dx2
            if abs(cross) < 1e-10:
                return None
            
            dx = p2_end.x() - p1_end.x()
            dy = p2_end.y() - p1_end.y()
            t1 = (dx * dy2 - dy * dx2) / cross
            
            intersection_x = p1_end.x() + t1 * dx1
            intersection_y = p1_end.y() + t1 * dy1
            return QgsPointXY(intersection_x, intersection_y)
        
        valid_intersections.sort(key=lambda x: x[1])
        return valid_intersections[0][0]
    
    def extend_line_to_point(self, line_geom, target_point):
        if not line_geom or not target_point:
            return None
        
        points = self._get_line_points(line_geom)
        
        if len(points) < 2:
            return None
        
        last_point = points[-1]
        second_last = points[-2]
        
        line_dx = last_point.x() - second_last.x()
        line_dy = last_point.y() - second_last.y()
        
        target_dx = target_point.x() - last_point.x()
        target_dy = target_point.y() - last_point.y()
        
        dot_product = line_dx * target_dx + line_dy * target_dy
        
        new_points = list(points)
        
        if dot_product >= 0:
            new_points.append(target_point)
        else:
            first_point = points[0]
            second_point = points[1]
            
            line_dx_start = first_point.x() - second_point.x()
            line_dy_start = first_point.y() - second_point.y()
            
            target_dx_start = target_point.x() - first_point.x()
            target_dy_start = target_point.y() - first_point.y()
            
            dot_product_start = line_dx_start * target_dx_start + line_dy_start * target_dy_start
            
            if dot_product_start >= 0:
                new_points.insert(0, target_point)
            else:
                new_points.append(target_point)
        
        return QgsGeometry.fromPolylineXY(new_points)
    
    def reset_tool(self):
        """Reseta a ferramenta para uma nova operação."""
        self.first_line = None
        self.second_line = None
        self.step = 0
        self.first_rubber_band.reset()
        self.second_rubber_band.reset()
        self.preview_rubber_band.reset()
        self.intersection_rubber_band.reset()
    
    def canvasReleaseEvent(self, event):
        """Captura quando o botão do mouse é solto."""
        # Compatibilidade Qt5/Qt6: MouseButton enum
        try:
            right_button = Qt.MouseButton.RightButton  # Qt6
        except AttributeError:
            right_button = Qt.RightButton  # Qt5
        
        if event.button() == right_button:
            self.reset_tool()
            self.canvas.unsetMapTool(self)
    
    def get_active_layer(self):
        """Obtém a camada ativa do projeto."""
        layer = self.iface.activeLayer()
        if layer and isinstance(layer, QgsVectorLayer):
            return layer
        return None
    
    def is_line_layer(self, layer):
        """Verifica se a camada é do tipo linha."""
        if not layer:
            return False
        return layer.geometryType() == QgsWkbTypes.LineGeometry
    
    def ensure_edit_mode(self, layer):
        """Verifica se a camada está em modo de edição."""
        if not layer:
            return False
        if not layer.isEditable():
            QMessageBox.warning(
                None,
                "Modo de Edição",
                "Por favor, habilite a edição da camada de linha antes de usar esta ferramenta."
            )
            return False
        return True
    
    def update_feature_geometry(self, layer, feature, new_geometry):
        """Atualiza a geometria de uma feição na camada."""
        if not layer or not feature or not new_geometry:
            return False
        
        if not self.ensure_edit_mode(layer):
                    return False
        
        success = layer.changeGeometry(feature.id(), new_geometry)
        
        if success:
            layer.updateExtents()
            layer.triggerRepaint()
            self.canvas.refresh()
        
        return success
    
    def create_rubber_band(self, geom_type=QgsWkbTypes.LineGeometry, color=None, width=2):
        """Cria um rubber band para preview visual."""
        rubber_band = QgsRubberBand(self.canvas, geom_type)
        
        if color is None:
            color = QColor(255, 0, 0, 180)
        
        rubber_band.setColor(color)
        rubber_band.setWidth(width)
        
        return rubber_band
    
    def clear_hover_highlight(self):
        """Limpa o highlight de hover."""
        if self.hover_rubber_band:
            self.hover_rubber_band.reset()
        self.hover_feature = None
        self.hover_layer = None
    
    def find_closest_line_at_point(self, point, layer=None):
        """Encontra a linha mais próxima de um ponto no mapa."""
        search_radius_map = self.canvas.mapSettings().mapUnitsPerPixel() * self.search_radius
        
        canvas_crs = self.canvas.mapSettings().destinationCrs()
        
        closest_feature = None
        closest_layer = None
        closest_geom = None
        min_distance = float('inf')
        
        layers_to_search = [layer] if layer else self.canvas.layers()
        
        for search_layer in layers_to_search:
            if not isinstance(search_layer, QgsVectorLayer):
                continue
            
            if search_layer.type() != QgsMapLayerType.VectorLayer:
                continue
            
            if search_layer.geometryType() != QgsWkbTypes.LineGeometry:
                continue
            
            point_in_layer_crs = self.transform_point_to_layer_crs(point, search_layer)
            
            layer_crs = search_layer.crs()
            search_radius_layer = search_radius_map
            
            if canvas_crs != layer_crs:
                try:
                    point2 = QgsPointXY(point.x() + search_radius_map, point.y())
                    point2_in_layer = self.transform_point_to_layer_crs(point2, search_layer)
                    search_radius_layer = point_in_layer_crs.distance(point2_in_layer)
                except:
                    pass
            
            search_rect = QgsRectangle(
                point_in_layer_crs.x() - search_radius_layer,
                point_in_layer_crs.y() - search_radius_layer,
                point_in_layer_crs.x() + search_radius_layer,
                point_in_layer_crs.y() + search_radius_layer
            )
            
            for feature in search_layer.getFeatures(QgsFeatureRequest(search_rect)):
                geom = feature.geometry()
                if not geom:
                    continue
                
                # Calcula distância do ponto à geometria (ambos no CRS da camada)
                point_geom = QgsGeometry.fromPointXY(point_in_layer_crs)
                distance = geom.distance(point_geom)
                
                if distance < min_distance and distance < search_radius_layer:
                    min_distance = distance
                    closest_feature = feature
                    closest_layer = search_layer
                    closest_geom = geom
        
        return closest_feature, closest_layer, closest_geom
    
    def update_hover_highlight(self, point):
        """Atualiza o highlight visual da linha sob o mouse."""
        # Busca a linha mais próxima apenas na camada ativa
        active_layer = self.iface.activeLayer()
        
        if not active_layer or active_layer.type() != QgsMapLayerType.VectorLayer or \
           active_layer.geometryType() != QgsWkbTypes.LineGeometry:
            self.clear_hover_highlight()
            return
            
        feature, layer, geom = self.find_closest_line_at_point(point, active_layer)
        
        if feature and geom:
            geom_in_canvas_crs = self.transform_geometry_to_canvas_crs(geom, layer)
            
            self.hover_rubber_band.reset(QgsWkbTypes.LineGeometry)
            self.hover_rubber_band.addGeometry(geom_in_canvas_crs)
            self.hover_feature = feature
            self.hover_layer = layer
        else:
            self.clear_hover_highlight()
    
    def transform_point_to_layer_crs(self, point, layer):
        """Transforma um ponto do CRS do canvas para o CRS da camada."""
        if not layer:
            return point
        
        canvas_crs = self.canvas.mapSettings().destinationCrs()
        layer_crs = layer.crs()
        
        if canvas_crs == layer_crs:
            return point
        
        try:
            transform = QgsCoordinateTransform(canvas_crs, layer_crs, QgsProject.instance())
            return transform.transform(point)
        except Exception as e:
            print(f"Erro ao transformar ponto: {str(e)}")
            return point
    
    def transform_geometry_to_canvas_crs(self, geometry, layer):
        """Transforma uma geometria do CRS da camada para o CRS do canvas."""
        if not layer or not geometry:
            return geometry
        
        canvas_crs = self.canvas.mapSettings().destinationCrs()
        layer_crs = layer.crs()
        
        if canvas_crs == layer_crs:
            return geometry
        
        try:
            geom_copy = QgsGeometry(geometry)
            transform = QgsCoordinateTransform(layer_crs, canvas_crs, QgsProject.instance())
            result = geom_copy.transform(transform)
            if result == 0:
                return geom_copy
            else:
                return geometry
        except Exception as e:
            print(f"Erro ao transformar geometria: {str(e)}")
            return geometry
    
    def deactivate(self):
        self.first_rubber_band.reset()
        self.second_rubber_band.reset()
        self.preview_rubber_band.reset()
        self.intersection_rubber_band.reset()
        self.clear_hover_highlight()
        self.reset_tool()
        super().deactivate()


def run(iface):
    canvas = iface.mapCanvas()
    tool = ChanfroTool(canvas, iface)
    canvas.setMapTool(tool)
    
    iface.messageBar().pushMessage(
        "Ferramenta Chanfro",
        "Clique na primeira linha.",
        level=Qgis.Info,
        duration=5
    )