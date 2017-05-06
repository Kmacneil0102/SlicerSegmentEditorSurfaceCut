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
    self.buttonToOperationNameMap = {}

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
    self.operationRadioButtons = []

    #Operation buttons
    self.eraseInsideButton = qt.QRadioButton("Erase inside")
    self.operationRadioButtons.append(self.eraseInsideButton)
    self.buttonToOperationNameMap[self.eraseInsideButton] = 'ERASE_INSIDE'

    self.eraseOutsideButton = qt.QRadioButton("Erase outside")
    self.operationRadioButtons.append(self.eraseOutsideButton)
    self.buttonToOperationNameMap[self.eraseOutsideButton] = 'ERASE_OUTSIDE'

    self.fillInsideButton = qt.QRadioButton("Fill inside")
    self.operationRadioButtons.append(self.fillInsideButton)
    self.buttonToOperationNameMap[self.fillInsideButton] = 'FILL_INSIDE'

    self.fillOutsideButton = qt.QRadioButton("Fill outside")
    self.operationRadioButtons.append(self.fillOutsideButton)
    self.buttonToOperationNameMap[self.fillOutsideButton] = 'FILL_OUTSIDE'

    #Operation buttons layout
    operationLayout = qt.QGridLayout()
    operationLayout.addWidget(self.eraseInsideButton, 0, 0)
    operationLayout.addWidget(self.eraseOutsideButton, 1, 0)
    operationLayout.addWidget(self.fillInsideButton, 0, 1)
    operationLayout.addWidget(self.fillOutsideButton, 1, 1)

    self.operationRadioButtons[2].setChecked(True)
    self.scriptedEffect.addLabeledOptionsWidget("Operation:", operationLayout)

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
    for button in self.operationRadioButtons:
      button.connect('toggled(bool)',
      lambda toggle, widget=self.buttonToOperationNameMap[button]: self.onOperationSelectionChanged(widget, toggle))
    self.applyButton.connect('clicked()', self.onApply)
    self.cancelButton.connect('clicked()', self.onCancel)
    self.fiducialPlacementToggle.placeButton().clicked.connect(self.onFiducialPlacementToggleChanged)

  def activate(self):
    self.scriptedEffect.showEffectCursorInSliceView = False
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

  def setMRMLDefaults(self):
    self.scriptedEffect.setParameterDefault("Operation", "FILL_INSIDE")

  def updateGUIFromMRML(self):
    self.cancelButton.setEnabled(self.clippingMarkupNode.GetNumberOfFiducials() is not 0)

  #
  # Effect specific methods (the above ones are the API methods to override)
  #

  def onOperationSelectionChanged(self, operationName, toggle):
    if not toggle:
      return
    self.scriptedEffect.setParameter("Operation", operationName)

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

    import vtkSegmentationCorePython as vtkSegmentationCore

    # Allow users revert to this state by clicking Undo
    self.scriptedEffect.saveStateForUndo()

    # This can be a long operation - indicate it to the user
    qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)

    if self.clippingMarkupNode and self.clippingMarkupNode.GetNumberOfFiducials() is not 0:
      operationName = self.scriptedEffect.parameter("Operation")
      modifierLabelmap = self.scriptedEffect.defaultModifierLabelmap()
      segmentationNode = self.scriptedEffect.parameterSetNode().GetSegmentationNode()
      WorldToModifierLabelmapIjkTransform = vtk.vtkTransform()

      WorldToModifierLabelmapIjkTransformer = vtk.vtkTransformPolyDataFilter()
      WorldToModifierLabelmapIjkTransformer.SetTransform(WorldToModifierLabelmapIjkTransform)
      WorldToModifierLabelmapIjkTransformer.SetInputConnection(self.clippingModel.GetPolyDataConnection())

      segmentationToSegmentationIjkTransformMatrix = vtk.vtkMatrix4x4()
      modifierLabelmap.GetImageToWorldMatrix(segmentationToSegmentationIjkTransformMatrix)
      segmentationToSegmentationIjkTransformMatrix.Invert()
      WorldToModifierLabelmapIjkTransform.Concatenate(segmentationToSegmentationIjkTransformMatrix)

      worldToSegmentationTransformMatrix = vtk.vtkMatrix4x4()
      slicer.vtkMRMLTransformNode.GetMatrixTransformBetweenNodes(None, segmentationNode.GetParentTransformNode(), worldToSegmentationTransformMatrix)
      WorldToModifierLabelmapIjkTransform.Concatenate(worldToSegmentationTransformMatrix)
      WorldToModifierLabelmapIjkTransformer.Update()

      polyToStencil = vtk.vtkPolyDataToImageStencil()
      polyToStencil.SetOutputSpacing(1.0, 1.0, 1.0)
      polyToStencil.SetInputConnection(WorldToModifierLabelmapIjkTransformer.GetOutputPort())
      boundsIjk = WorldToModifierLabelmapIjkTransformer.GetOutput().GetBounds()
      modifierLabelmapExtent = self.scriptedEffect.modifierLabelmap().GetExtent()
      polyToStencil.SetOutputWholeExtent(modifierLabelmapExtent[0], modifierLabelmapExtent[1], modifierLabelmapExtent[2], modifierLabelmapExtent[3], int(round(boundsIjk[4])), int(round(boundsIjk[5])))
      polyToStencil.Update()

      stencilData = polyToStencil.GetOutput()
      stencilExtent = [0, -1, 0, -1, 0, -1]
      stencilData.SetExtent(stencilExtent)

      stencilToImage = vtk.vtkImageStencilToImage()
      stencilToImage.SetInputConnection(polyToStencil.GetOutputPort())
      if operationName == "FILL_INSIDE" or operationName == "ERASE_INSIDE":
        stencilToImage.SetInsideValue(1.0)
        stencilToImage.SetOutsideValue(0.0)
      else:
        stencilToImage.SetInsideValue(0.0)
        stencilToImage.SetOutsideValue(1.0)
      stencilToImage.SetOutputScalarType(modifierLabelmap.GetScalarType())

      stencilPositioner = vtk.vtkImageChangeInformation()
      stencilPositioner.SetInputConnection(stencilToImage.GetOutputPort())
      stencilPositioner.SetOutputSpacing(modifierLabelmap.GetSpacing())
      stencilPositioner.SetOutputOrigin(modifierLabelmap.GetOrigin())

      stencilPositioner.Update()
      orientedStencilPositionerOuput = vtkSegmentationCore.vtkOrientedImageData()
      orientedStencilPositionerOuput.ShallowCopy(stencilToImage.GetOutput())
      imageToWorld = vtk.vtkMatrix4x4()
      modifierLabelmap.GetImageToWorldMatrix(imageToWorld)
      orientedStencilPositionerOuput.SetImageToWorldMatrix(imageToWorld)

      vtkSegmentationCore.vtkOrientedImageDataResample.ModifyImage(modifierLabelmap, orientedStencilPositionerOuput, vtkSegmentationCore.vtkOrientedImageDataResample.OPERATION_MAXIMUM)

      modMode = slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeAdd
      if operationName == "ERASE_INSIDE" or operationName == "ERASE_OUTSIDE":
        modMode = slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeRemove

      self.scriptedEffect.modifySelectedSegmentByLabelmap(modifierLabelmap, modMode)

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
