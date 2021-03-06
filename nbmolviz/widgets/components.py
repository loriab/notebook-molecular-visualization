# Copyright 2017 Autodesk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import collections

import ipywidgets as ipy
import traitlets
from moldesign import units as u
from moldesign import utils

from .. import viewers
from ..widget_utils import process_widget_kwargs
from .selector import Selector


class AtomInspector(ipy.HTML, Selector):
    """
    Turn atom indices into a value to display
    """
    def indices_to_value(self, atom_indices, atoms):
        indicated_atoms = map(lambda index: atoms[index], atom_indices)
        return self.atoms_to_value(indicated_atoms)

    """
    Turn atom objects into a value to display
    """
    def atoms_to_value(self, atoms):
        if len(atoms) == 0:
            return 'No selection'
        elif len(atoms) == 1:
            atom = atoms[0]
            res = atom.residue
            chain = res.chain
            lines = ["<b>Molecule</b>: %s<br>" % atom.molecule.name]
            if atom.chain.name is not None:
                lines.append("<b>Chain</b> %s<br>" % chain.name)
            if atom.residue.type != 'placeholder':
                lines.append("<b>Residue</b> %s, index %d<br>" % (res.name, res.index))
            lines.append("<b>Atom</b> %s (%s), index %d<br>" % (atom.name, atom.symbol, atom.index))
            return '\n'.join(lines)

        elif len(atoms) > 1:
            atstrings = ['<b>%s</b>, index %s / res <b>%s</b>, index %s / chain <b>%s</b>' %
                         (a.name, a.index, a.residue.resname, a.residue.index, a.chain.name)
                         for a in atoms]
            return '<br>'.join(atstrings)


class ViewerToolBase(ipy.Box):
    """
    The base for most viewer-based widgets - it consists of a viewer in the top-left,
    UI controls on the right, and some additional widgets underneath the viewer
    """
    VIEWERTYPE = viewers.GeometryViewer

    def __init__(self, mol):
        self.mol = mol

        self.toolpane = ipy.VBox()
        self.viewer = self.VIEWERTYPE(mol)

        self.subtools = ipy.Box()
        self.viewer_pane = ipy.VBox([self.viewer, self.subtools])
        self.main_pane = ipy.HBox([self.viewer_pane, self.toolpane])

        super(ViewerToolBase, self).__init__([self.main_pane])

    def __getattr__(self, item):
        if hasattr(self.viewer, item):
            return getattr(self.viewer, item)
        else:
            raise AttributeError(item)


class SelBase(ViewerToolBase):
    def __init__(self, mol):
        super(SelBase, self).__init__(mol)

        self._atomset = collections.OrderedDict()

        self.atom_listname = ipy.HTML('<b>Selected atoms:</b>')
        self.atom_list = ipy.SelectMultiple(options=list(self.viewer.selected_atom_indices),
                                            layout=ipy.Layout(height='150px'))
        traitlets.directional_link(
            (self.viewer, 'selected_atom_indices'),
            (self.atom_list, 'options'),
            self._atom_indices_to_atoms
        )

        self.select_all_atoms_button = ipy.Button(description='Select all atoms')
        self.select_all_atoms_button.on_click(self.select_all_atoms)

        self.select_none = ipy.Button(description='Clear all selections')
        self.select_none.on_click(self.clear_selections)

    @property
    def selected_atoms(self):
        return self._atom_indices_to_atoms(self.viewer.selected_atom_indices)

    def remove_atomlist_highlight(self, *args):
        self.atom_list.value = tuple()

    @staticmethod
    def atomkey(atom):
        return '%s (index %d)' % (atom.name, atom.index)

    def _atom_indices_to_atoms(self, atom_indices):
        return [self.mol.atoms[atom_index] for atom_index in atom_indices]

    def select_all_atoms(self, *args):
        self.viewer.selected_atom_indices = set(i for i, atom in enumerate(self.mol.atoms))

    def clear_selections(self, *args):
        self.viewer.selected_atom_indices = set()


class ReadoutFloatSlider(ipy.Box):
    description = traitlets.Unicode()
    value = traitlets.Float()

    def __init__(self, format=None, *args, **kwargs):
        description = kwargs.pop('description', 'FloatSlider')
        min = kwargs.setdefault('min', 0.0)
        max = kwargs.setdefault('max', 10.0)
        self.formatstring = format
        self.header = ipy.HTML()
        self.readout = ipy.Text(width=100)
        self.readout.on_submit(self.parse_value)

        kwargs.setdefault('readout', False)
        self.slider = ipy.FloatSlider(*args, **process_widget_kwargs(kwargs))
        self.minlabel = ipy.HTML(u'<font size=1.5>{}</font>'.format(self.formatstring.format(min)))
        self.maxlabel = ipy.HTML(u'<font size=1.5>{}</font>'.format(self.formatstring.format(max)))
        self.sliderbox = ipy.HBox([self.minlabel, self.slider, self.maxlabel])
        traitlets.link((self, 'description'), (self.header, 'value'))
        traitlets.link((self, 'value'), (self.slider, 'value'))
        self.description = description
        self.update_readout()
        super(ReadoutFloatSlider, self).__init__([self.header,
                                                  self.readout,
                                                  self.sliderbox])

    @traitlets.observe('value')
    def update_readout(self, *args):
        self.readout.value = self.formatstring.format(self.value)

    def disable(self):
        self.slider.disabled = True
        self.readout.disabled = True

    def enable(self):
        self.slider.disabled = False
        self.readout.disabled = False

    def parse_value(self, *args):
        try:
            f = float(self.readout.value)
        except ValueError:
            s = self.readout.value
            match = utils.GETFLOAT.search(s)
            if match is None:
                self.readout.value = self.formatstring.format(self.slider.value)
                print "Couldn't parse string %s" % s
                return
            else:
                f = float(s[match.start():match.end()])
        self.slider.value = f

