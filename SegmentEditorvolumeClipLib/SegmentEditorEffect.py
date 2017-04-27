import os
import vtk, qt, ctk, slicer
import logging
from SegmentEditorEffects import *

class SegmentEditorEffect(AbstractScriptedSegmentEditorEffect):
  """This effect uses markup fiducials to segment the input volume"""

  def __init__(self, scriptedEffect):
    scriptedEffect.name = 'Volume Clip'
    scriptedEffect.perSegment = True # this effect operates on a single selected segment
    AbstractScriptedSegmentEditorEffect.__init__(self, scriptedEffect)

    # Effect-specific members
    self.clippingMarkupNode = None
    self.clippingModel = None
    self.clippingMarkupNodeObserver = None

  def clone(self):
    # It should not be necessary to modify this method
    import qSlicerSegmentationsEditorEffectsPythonQt as effects
    clonedEffect = effects.qSlicerSegmentEditorScriptedEffect(None)
    clonedEffect.setPythonSource(__file__.replace('\\','/'))
    return clonedEffect

  def icon(self):
    # It should not be necessary to modify this method
    iconPath = os.path.join(os.path.dirname(__file__), 'SegmentEditorEffect.png')
    if os.path.exists(iconPath):
      return qt.QIcon(iconPath)
    return qt.QIcon()

  def helpText(self):
    return """Use markup fiducials to create a segment outline. The surface is then generated from these points. All previous contents of the selected segmented are overwritten on Apply.
"""

  def setupOptionsFrame(self):

    #Fiducial Placement widget
    self.fiducialPlacementToggle = slicer.qSlicerMarkupsPlaceWidget()
    self.fiducialPlacementToggle.setMRMLScene(slicer.mrmlScene)
    self.fiducialPlacementToggle.placeMultipleMarkups = self.fiducialPlacementToggle.ForcePlaceMultipleMarkups
    self.fiducialPlacementToggle.buttonsVisible = False
    self.scriptedEffect.addLabeledOptionsWidget("Fiducial Placement: ", self.fiducialPlacementToggle)
    self.fiducialPlacementToggle.show()
    self.fiducialPlacementToggle.placeButton().show()
    self.fiducialPlacementToggle.deleteButton().show()

    # Apply button
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.objectName = self.__class__.__name__ + 'Apply'
    self.applyButton.setToolTip("Generate surface from markup fiducials.")
    self.scriptedEffect.addOptionsWidget(self.applyButton)

    # Cancel Button
    self.cancelButton = qt.QPushButton("Cancel")
    self.cancelButton.objectName = self.__class__.__name__ + 'Cancel'
    self.cancelButton.setToolTip("Clear fiducials and remove from scene.")

    #Finish action buttons
    finishAction = qt.QHBoxLayout()
    finishAction.addWidget(self.cancelButton)
    finishAction.addWidget(self.applyButton)
    self.scriptedEffect.addOptionsWidget(finishAction)

    # connections
    self.applyButton.connect('clicked()', self.onApply)
    self.cancelButton.connect('clicked()', self.onCancel)
    self.fiducialPlacementToggle.placeButton().clicked.connect(self.onFiducialPlacementToggleChanged)

  def activate(self):
    # Create empty markup fiducial node
    if not self.clippingMarkupNode:
      self.createNewMarkupNode()
      self.fiducialPlacementToggle.setCurrentNode(self.clippingMarkupNode)
      self.setAndObserveClippingMarkupNode(self.clippingMarkupNode)
      self.fiducialPlacementToggle.setPlaceModeEnabled(False)

  def deactivate(self):
    self.reset()

  def createCursor(self, widget):
    # Turn off effect-specific cursor for this effect
    return slicer.util.mainWindow().cursor

  def updateGUIFromMRML(self):
    self.cancelButton.setEnabled(self.clippingMarkupNode.GetNumberOfFiducials() is not 0)

  #
  # Effect specific methods (the above ones are the API methods to override)
  #

  def onFiducialPlacementToggleChanged(self):
    #print(self.fiducialPlacementToggle.placeModeEnabled)
    if self.fiducialPlacementToggle.placeButton().isChecked():
      # Create empty model node
      if self.clippingModel is None:
        self.clippingModel = slicer.vtkMRMLModelNode()
        slicer.mrmlScene.AddNode(self.clippingModel)

      # Create empty markup fiducial node
      if self.clippingMarkupNode is None:
        self.createNewMarkupNode()
        self.fiducialPlacementToggle.setCurrentNode(self.clippingMarkupNode)

  def onCancel(self):
    self.reset()
    self.createNewMarkupNode()
    self.fiducialPlacementToggle.setCurrentNode(self.clippingMarkupNode)

  def reset(self):
    if self.fiducialPlacementToggle.placeModeEnabled:
      self.fiducialPlacementToggle.setPlaceModeEnabled(False)

    if self.clippingModel:
      slicer.mrmlScene.RemoveNode(self.clippingModel)
      self.clippingModel = None

    if self.clippingMarkupNode:
      slicer.mrmlScene.RemoveNode(self.clippingMarkupNode)
      self.setAndObserveClippingMarkupNode(None)

  def onApply(self):

    # Allow users revert to this state by clicking Undo
    self.scriptedEffect.saveStateForUndo()

    # This can be a long operation - indicate it to the user
    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)

    if self.clippingMarkupNode and self.clippingMarkupNode.GetNumberOfFiducials() is not 0:
      l = slicer.vtkSlicerSegmentationsModuleLogic
      seg = slicer.util.getNode('Segmentation')
      s = l.CreateSegmentFromModelNode(self.clippingModel, seg)

      segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
      s.SetName(segmentID)
      seg.GetSegmentation().GetSegment(segmentID).DeepCopy(s)

    self.reset()
    self.createNewMarkupNode()
    self.fiducialPlacementToggle.setCurrentNode(self.clippingMarkupNode)

    qt.QApplication.restoreOverrideCursor()

  def createNewMarkupNode(self):
    # Create empty markup fiducial node
    if self.clippingMarkupNode is None:
      displayNode = slicer.vtkMRMLMarkupsDisplayNode()
      slicer.mrmlScene.AddNode(displayNode)
      self.clippingMarkupNode = slicer.vtkMRMLMarkupsFiducialNode()
      self.clippingMarkupNode.SetName('C')
      slicer.mrmlScene.AddNode(self.clippingMarkupNode)
      self.clippingMarkupNode.SetAndObserveDisplayNodeID(displayNode.GetID())
      self.setAndObserveClippingMarkupNode(self.clippingMarkupNode)
      self.updateGUIFromMRML()


  def setAndObserveClippingMarkupNode(self, clippingMarkupNode):
    if clippingMarkupNode == self.clippingMarkupNode and self.clippingMarkupNodeObserver:
      # no change and node is already observed
      return
    # Remove observer to old parameter node
    if self.clippingMarkupNode and self.clippingMarkupNodeObserver:
      self.clippingMarkupNode.RemoveObserver(self.clippingMarkupNodeObserver)
      self.clippingMarkupNodeObserver = None
    # Set and observe new parameter node
    self.clippingMarkupNode = clippingMarkupNode
    if self.clippingMarkupNode:
      self.clippingMarkupNodeObserver = self.clippingMarkupNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.onClippingMarkupNodeModified)
    # Update GUI
    self.updateModelFromClippingMarkupNode()

  def onClippingMarkupNodeModified(self, observer, eventid):
    self.updateModelFromClippingMarkupNode()
    self.updateGUIFromMRML()

  def updateModelFromClippingMarkupNode(self):
    if not self.clippingMarkupNode or not self.clippingModel:
      return
    self.updateModelFromMarkup(self.clippingMarkupNode, self.clippingModel)

  def updateModelFromMarkup(self, inputMarkup, outputModel):
    """
    Update model to enclose all points in the input markup list
    """

    # Delaunay triangulation is robust and creates nice smooth surfaces from a small number of points,
    # however it can only generate convex surfaces robustly.
    useDelaunay = True

    # Create polydata point set from markup points

    points = vtk.vtkPoints()
    cellArray = vtk.vtkCellArray()

    numberOfPoints = inputMarkup.GetNumberOfFiducials()

    # Surface generation algorithms behave unpredictably when there are not enough points
    # return if there are very few points
    if useDelaunay:
      if numberOfPoints < 3:
        return
    else:
      if numberOfPoints < 10:
        return

    points.SetNumberOfPoints(numberOfPoints)
    new_coord = [0.0, 0.0, 0.0]

    for i in range(numberOfPoints):
      inputMarkup.GetNthFiducialPosition(i, new_coord)
      points.SetPoint(i, new_coord)

    cellArray.InsertNextCell(numberOfPoints)
    for i in range(numberOfPoints):
      cellArray.InsertCellPoint(i)

    pointPolyData = vtk.vtkPolyData()
    pointPolyData.SetLines(cellArray)
    pointPolyData.SetPoints(points)

    # Create surface from point set

    if useDelaunay:

      delaunay = vtk.vtkDelaunay3D()
      delaunay.SetInputData(pointPolyData)

      surfaceFilter = vtk.vtkDataSetSurfaceFilter()
      surfaceFilter.SetInputConnection(delaunay.GetOutputPort())

      smoother = vtk.vtkButterflySubdivisionFilter()
      smoother.SetInputConnection(surfaceFilter.GetOutputPort())
      smoother.SetNumberOfSubdivisions(3)
      smoother.Update()

      outputModel.SetPolyDataConnection(smoother.GetOutputPort())

    else:

      surf = vtk.vtkSurfaceReconstructionFilter()
      surf.SetInputData(pointPolyData)
      surf.SetNeighborhoodSize(20)
      surf.SetSampleSpacing(
        80)  # lower value follows the small details more closely but more dense pointset is needed as input

      cf = vtk.vtkContourFilter()
      cf.SetInputConnection(surf.GetOutputPort())
      cf.SetValue(0, 0.0)

      # Sometimes the contouring algorithm can create a volume whose gradient
      # vector and ordering of polygon (using the right hand rule) are
      # inconsistent. vtkReverseSense cures this problem.
      reverse = vtk.vtkReverseSense()
      reverse.SetInputConnection(cf.GetOutputPort())
      reverse.ReverseCellsOff()
      reverse.ReverseNormalsOff()

      outputModel.SetPolyDataConnection(reverse.GetOutputPort())

    # Create default model display node if does not exist yet
    if not outputModel.GetDisplayNode():
      modelDisplayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelDisplayNode")

      # Get color of edited segment
      segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
      displayNode = segmentationNode.GetDisplayNode()
      if displayNode is None:
        logging.error("preview: Invalid segmentation display node!")
        color = [0.5, 0.5, 0.5]
      segmentID = self.scriptedEffect.parameterSetNode().GetSelectedSegmentID()
      r, g, b = segmentationNode.GetSegmentation().GetSegment(segmentID).GetColor()

      modelDisplayNode.SetColor(r, g, b)  # Edited segment color
      modelDisplayNode.BackfaceCullingOff()
      modelDisplayNode.SliceIntersectionVisibilityOn()
      modelDisplayNode.SetOpacity(0.3)  # Between 0-1, 1 being opaque
      slicer.mrmlScene.AddNode(modelDisplayNode)
      outputModel.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())

    outputModel.GetDisplayNode().SliceIntersectionVisibilityOn()

    outputModel.Modified()
