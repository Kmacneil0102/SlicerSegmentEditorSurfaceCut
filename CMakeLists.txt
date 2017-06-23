cmake_minimum_required(VERSION 2.8.9)


#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/Kmacneil0102/SlicerSegmentEditorSurfaceCut")
set(EXTENSION_CATEGORY "Segmentation")
set(EXTENSION_CONTRIBUTORS "Kyle MacNeil")
set(EXTENSION_DESCRIPTION "Effect for Segment Editor")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/kmacneil0102/SlicerSegmentEditorSurfaceCut/master/SegmentEditorSurfaceCutLib/SegmentEditorEffect.png")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(SegmentEditorSurfaceCut)

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
