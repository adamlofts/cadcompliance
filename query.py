from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.BRep import BRep_Tool
from OCP.BRepTools import BRepTools
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.OCP.TCollection import TCollection_ExtendedString, TCollection_AsciiString

def load_step():
    # Load STEP file
    step_path = "sphere.step"
    reader = STEPControl_Reader()
    status = reader.ReadFile(step_path)

    if status == IFSelect_RetDone:
        reader.TransferRoots()
        shape = reader.OneShape()

        # Optionally mesh the shape for visualization
        mesh = BRepMesh_IncrementalMesh(shape, 0.1)
        mesh.Perform()

        # You now have the full TopoDS_Shape
        print("Shape loaded:", shape)
    else:
        print("Failed to load STEP file")


from OCP.TDocStd import TDocStd_Document
from OCP.TDF import TDF_LabelSequence
from OCP.XCAFApp import XCAFApp_Application
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_AssemblyTool, XCAFDoc_ShapeTool, XCAFDoc_AssemblyGraph, XCAFDoc_AssemblyIterator
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDF import TDF_Label, TDF_Tool
from OCP.TNaming import TNaming_NamedShape
from OCP.TDataStd import TDataStd_Name
from OCP.BRepTools import BRepTools

# Setup the OCCT application/document framework
def new_doc():
    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString("str"))
    app.NewDocument(TCollection_ExtendedString("MDTV-CAF"), doc)
    return doc

# Load STEP file into CAF document
def load_step_to_doc(path: str):
    doc = new_doc()
    reader = STEPCAFControl_Reader()
    reader.SetColorMode(True)
    reader.SetNameMode(True)
    reader.SetLayerMode(True)

    if not reader.ReadFile(path):
        raise RuntimeError("Failed to read STEP file")

    reader.Transfer(doc)
    return doc

# Recursively walk the assembly tree
def walk_assembly(label: TDF_Label, assembly_tool: XCAFDoc_AssemblyTool, shape_tool: XCAFDoc_ShapeTool, indent=0):
    name = ""
    import pdb
    pdb.set_trace()
    if label.FindAttribute(TDataStd_Name(), False):
        name_attr = TDataStd_Name()
        if label.FindAttribute(TDataStd_Name(), name_attr):
            name = name_attr.Get().ToCString()
    else:
        name = "(no name)"

    shape = shape_tool.GetShape(label)

    print("  " * indent + f"{name}")

    if assembly_tool.IsAssembly(label):
        # This is an assembly node with children
        children = TDF_LabelSequence()
        assembly_tool.GetComponents(label, children)
        for i in range(children.Length()):
            child_label = children.Value(i + 1)
            walk_assembly(child_label, assembly_tool, shape_tool, indent + 1)

# Main
doc = load_step_to_doc("Formula Student Concept v1.step")
# doc = load_step_to_doc("sphere.step")

# Access tools
shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
graph = XCAFDoc_AssemblyGraph(doc)

# https://github.com/KiCad/kicad-source-mirror/blob/9f7fa4df662905ea52bc0b5915e477b0333fb1c3/pcbnew/exporters/step/step_pcb_model.cpp#L541
for i in range(1, graph.NbNodes() + 1):
    node_type = graph.GetNodeType( i )
    node = graph.GetNode( i )
    # print(node_type)
    # print(node)
    # s = TCollection_AsciiString()
    # v = TDF_Tool.Entry_s( node, s)
    attr = TDataStd_Name()
    node.FindAttribute(TDataStd_Name().ID(), attr)
    print(attr.Get().ToExtString())

# it = XCAFDoc_AssemblyIterator(doc)
#
# while it.More():
#     item = it.Current()
#     print(item)
#     import pdb
#     pdb.set_trace()
#     it.Next()
# #
# # Iterate over graph nodes
# it = graph.GetIterator()
# while it.More():
#     label = it.Current()
#
#     # Try to extract name
#     if label.FindAttribute(TDataStd_Name.GetID()):
#         name_attr = TDataStd_Name.DownCast(label.FindAttribute(TDataStd_Name.GetID()))
#         name = name_attr.Get().ToCString()
#     else:
#         name = "(unnamed)"
#
#     print("Node:", name)
#
#     it.Next()
#

# assembly_tool = XCAFDoc_AssemblyTool()
#
# # Get top-level shapes (typically 1 root assembly)
# roots = TDF_LabelSequence()
# shape_tool.GetFreeShapes(roots)
#
# for i in range(roots.Length()):
#     label = roots.Value(i + 1)
#     walk_assembly(label, assembly_tool, shape_tool)
