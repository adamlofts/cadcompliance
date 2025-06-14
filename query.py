import io
from typing import List

from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.IFSelect import IFSelect_RetDone
from OCP.OCP.TCollection import TCollection_ExtendedString
from OCP.STEPControl import STEPControl_Reader
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()


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
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_AssemblyTool, XCAFDoc_ShapeTool, XCAFDoc_AssemblyGraph
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDF import TDF_Label
from OCP.TDataStd import TDataStd_Name


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

def list_integers(packedmap):
    for i in range(packedmap.GetMinimalMapped(), packedmap.GetMaximalMapped() + 1):
        if packedmap.Contains(i):
            yield i


def recurse(label, depth, func):
    node_type = graph.GetNodeType(label)
    node = graph.GetNode(label)
    # print(node_type)
    # print(node)
    # s = TCollection_AsciiString()
    # v = TDF_Tool.Entry_s( node, s)
    attr = TDataStd_Name()
    node.FindAttribute(TDataStd_Name().ID(), attr)
    print(f"{'  ' * depth} [{node_type}] {attr.Get().ToExtString()}")

    func(node, node_type, depth)

    if graph.HasChildren(label):
        for child in list_integers(graph.GetChildren(label)):
            recurse(child, depth + 1, func)

textio = io.StringIO()

def write_node_text(node, node_type, depth):
    attr = TDataStd_Name()
    node.FindAttribute(TDataStd_Name().ID(), attr)
    textio.write(f"{'  ' * depth} [{node_type}] {attr.Get().ToExtString()}\n")

for root in list_integers(graph.GetRoots()):
    recurse(root, 0, write_node_text)

textio.seek(0)
text = textio.read()

client = OpenAI()


class AssemblyNode(BaseModel):
    name: str
    reason: str


class Matches(BaseModel):
    items: List[AssemblyNode]



response = client.responses.parse(
    model="gpt-4o-2024-08-06",
    input=[
        {"role": "system", "content": """You will be given a CAD assembly tree for a formula student car.
Return a JSON string array, with a name for each node, representing wheels."""},
        {
            "role": "user",
            "content":  text,
        },
    ],
    text_format=Matches,
)

matches = response.output_parsed

import pdb
pdb.set_trace()
for match in matches.items:
    print(f"Match: {match}")
