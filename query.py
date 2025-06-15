import base64
import io
import subprocess
import tempfile
from typing import List

from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.IFSelect import IFSelect_RetDone
from OCP.OCP.TCollection import TCollection_ExtendedString
from OCP.OCP.TopoDS import TopoDS_Shape
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
    # print(f"{'  ' * depth} [{node_type}] {attr.Get().ToExtString()}")

    has_children = graph.HasChildren(label)
    func(node, node_type, depth, has_children)

    if has_children:
        for child in list_integers(graph.GetChildren(label)):
            recurse(child, depth + 1, func)

def find_wheels_by_name_in_tree():
    textio = io.StringIO()

    def write_node_text(node, node_type, depth, has_children):
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
    for match in matches.items:
        print(f"Match: {match}")

    wheel_names = [match.name for match in matches.items]

    match_labels = []

    def collect_match(node, node_type, depth, has_children):
        # only match occurences
        if node_type != XCAFDoc_AssemblyGraph.NodeType_Occurrence:
            return

        attr = TDataStd_Name()
        node.FindAttribute(TDataStd_Name().ID(), attr)
        if attr.Get().ToExtString() in wheel_names:
            match_labels.append(node)

    for root in list_integers(graph.GetRoots()):
        recurse(root, 0, collect_match)

    for match_label in match_labels:
        print(f"Match: {match_label}")

    return match_labels


def find_wheels_visually():

    client = OpenAI()

    all_leaf_shapes = []
    def _all(label, node_type, depth, has_children):
        if has_children:
            return  # only test leafs
        all_leaf_shapes.append(get_shape_from_label(label))

    for rlabel in list_integers(graph.GetRoots()):
        recurse(rlabel, 0, _all)

    match_labels = []
    def _test_visually(label, node_type, depth, has_children):
        if has_children:
            return  # only test leafs

        attr = TDataStd_Name()
        label.FindAttribute(TDataStd_Name().ID(), attr)

        test_shape = get_shape_from_label(label)

        grey_shapes = [shape for shape in all_leaf_shapes if not shape.IsEqual(test_shape)]
        red_shapes = [test_shape]

        if 'Wheel' not in attr.Get().ToExtString():
            return

        fname = f'test-{attr.Get().ToExtString()}.png'
        render(grey_shapes, red_shapes, fname)

        with open(fname, "rb") as image_file:
            b64 = base64.b64encode(image_file.read()).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """You will be shown a CAD model of an open wheel race car. 
                One solid will be RED. If nothing is highlighted then respond with the word none.
                Is the red highlighted component a wheel, tyre, rim or a part of the wheel? Either at the front or
                back. Do not count the suspension.
                If so, respond with the word yes. Otherwise say no and why not"""},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{b64}"
                    }}
                ]}
            ],
        )

        content = response.choices[0].message.content

        is_yes = 'yes' in content.lower()
        print(f"test: [{is_yes and "YES" or "NO"}] [{node_type}] {attr.Get().ToExtString()} -> {content}")
        if is_yes:
            match_labels.append(label)

    for label in list_integers(graph.GetRoots()):
        recurse(label, 0, _test_visually)

    return match_labels


def get_shape_from_label(label: TDF_Label) -> TopoDS_Shape:
    # Given an XCAF ShapeTool and a label, return the TopoDS_Shape stored in the label.
    shape = TopoDS_Shape()
    assert(XCAFDoc_ShapeTool().GetShape_s(label, shape))
    return shape

from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Pnt, gp_Vec, gp_Ax2, gp_Dir

def get_center_of_mass(shape):
    """
    Compute the center of mass of the given TopoDS_Shape.

    Parameters:
        shape (TopoDS_Shape): The shape to compute the center of mass for.

    Returns:
        (x, y, z): Coordinates of the center of mass.
    """
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    com = props.CentreOfMass()
    return com


from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.AIS import AIS_Shape
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.TopAbs import TopAbs_ShapeEnum

def check_rule_2_1_3(graph, wheel, axis):
    """ No part of the vehicle may enter a keep-out-zone defined by two lines extending vertically
from positions 75 mm in front of and 75 mm behind the outer diameter of the front and
rear tyres in the side view of the vehicle, with steering straight ahead. This keep-out zone
extends laterally from the outside plane of the wheel/tyre to the inboard plane of the
wheel/tyre assembly. """

    # Create bounding box of wheel
    box = Bnd_Box()
    BRepBndLib().Add_s(wheel, box)

    [xmin, ymin, zmin, xmax, ymax, zmax] = box.Get()

    # Make a box solid
    bbox_shape = BRepPrimAPI_MakeBox(gp_Pnt(xmin, ymin, zmin), gp_Pnt(xmax, ymax, zmax)).Shape()

    intersection_shapes = []
    intersection_labels = []

    def _check(node, node_type, depth, has_children):
        shape = get_shape_from_label(node)

        if shape.IsEqual(wheel):
            return  # no self test

        if has_children:
            return  # only test leafs

        intersection = BRepAlgoAPI_Common(shape, bbox_shape)
        intersection.Build()
        intersection_shape = intersection.Shape()
        # shape_type = intersection_shape.ShapeType()
        if intersection.HasGenerated():
            intersection_shapes.append(intersection_shape)
            intersection_labels.append(node)

    for root in list_integers(graph.GetRoots()):
        recurse(root, 0, _check)

    return intersection_shapes and (intersection_shapes[0], intersection_labels[0]) or None


from OCP.StlAPI import StlAPI_Writer


from OCP.TopoDS import TopoDS_Shape, TopoDS_Solid
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_ShapeEnum
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopoDS import TopoDS_Shape


def get_first_solid(shape: TopoDS_Shape) -> TopoDS_Shape | None:
    explorer = TopExp_Explorer(shape, TopAbs_ShapeEnum.TopAbs_SOLID)
    if explorer.More():
        return explorer.Current()
    return None


def write_stl(shape, fname):
    # Create an STL writer
    writer = StlAPI_Writer()
    writer.ASCIIMode = False

    solid = get_first_solid(shape)

    mesh = BRepMesh_IncrementalMesh(solid, 0.1, True, 0.5, True)

    # Write the shape to STL
    assert(writer.Write(solid, fname))


def render(grey_shapes, red_shapes, filename):

    grey_files = [tempfile.NamedTemporaryFile(delete_on_close=False) for _ in grey_shapes]
    red_files = [tempfile.NamedTemporaryFile(delete_on_close=False, prefix='red') for _ in red_shapes]

    for file, shape in zip(grey_files, grey_shapes):
        write_stl(shape, file.name)

    for file, shape in zip(red_files, red_shapes):
        write_stl(shape, file.name)

    files = [f.name for f in grey_files] + [f.name for f in red_files]
    subprocess.run(['blender', '--background', '--python', 'render_scene.py', '--'] +
                   files, capture_output=True)
    with open(filename, 'wb') as f:
        with open('output.png', 'rb') as inf:
            f.write(inf.read())


###


match_labels = find_wheels_visually()
match_shapes = [get_shape_from_label(label) for label in match_labels]

coms = [get_center_of_mass(shape) for shape in match_shapes]

for com in coms:
    print(f"COM: {com.X()},{com.Y()},{com.Z()}")

def find_coord_system(coms):
    # Find the car coordinate system using 3 points
    a = coms[0]
    b = coms[1]
    c = coms[2]

    v1 = gp_Vec(a, b)
    v2 = gp_Vec(a, c)

    # "forward" direction is largest vec, so swap so v1 is biggest
    if v2.Magnitude() > v1.Magnitude():
        t = v1
        v1 = v2
        v2 = t

    axis = gp_Ax2(a, gp_Dir(v1.Crossed(v2)), gp_Dir(v1))  # pnt, normal, Vx
    return axis

axis = None# find_coord_system(coms)

for match_shape, match_label in zip(match_shapes, match_labels):
    result = check_rule_2_1_3(graph, match_shape, axis)
    if not result:
        continue
    intersection_shape, intersection_label = result

    attr = TDataStd_Name()
    match_label.FindAttribute(TDataStd_Name().ID(), attr)
    intersection_attr = TDataStd_Name()
    intersection_label.FindAttribute(TDataStd_Name().ID(), intersection_attr)
    print(f'intersection with [{attr.Get().ToExtString()}] and [{intersection_attr.Get().ToExtString()}]')
    # write_stl(intersection_shape, 'shape.stl')


    render(match_shapes, [intersection_shape], f'inter-{attr.Get().ToExtString()}.png')





