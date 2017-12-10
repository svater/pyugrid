#!/usr/bin/env python

"""
Tests for saving a UGrid in netcdf format.

Designed to be run with pytest.

"""

from __future__ import (absolute_import, division, print_function)

import os
import netCDF4
import numpy as np

from pyugrid.ugrid import UGrid, UVar

from utilities import chdir, two_triangles, twenty_one_triangles

test_files = os.path.join(os.path.dirname(__file__), 'files')


def nc_has_variable(ds, var_name):
    """
    Checks that a netcdf file has the given variable defined.

    :param ds: a netCDF4.Dataset object, or a netcdf file name.

    """
    if not isinstance(ds, netCDF4.Dataset):
        ds = netCDF4.Dataset(ds)

    if var_name in ds.variables:
        return True
    else:
        print('{} is not a variable in the Dataset'.format(var_name))
        return False


def nc_has_dimension(ds, dim_name):
    """
    Checks that a netcdf file has the given dimension defined.

    :param ds: a netCDF4.Dataset object, or a netcdf file name.

    """
    if not isinstance(ds, netCDF4.Dataset):
        ds = netCDF4.Dataset(ds)
    if dim_name in ds.dimensions:
        return True
    else:
        return False


def nc_var_has_attr(ds, var_name, att_name):
    """
    Checks that the variable, var_name, has the attribute, att_name.

    """
    if not isinstance(ds, netCDF4.Dataset):
        ds = netCDF4.Dataset(ds)

    try:
        getattr(ds.variables[var_name], att_name)
        return True
    except AttributeError:
        return False


def nc_var_has_attr_vals(ds, var_name, att_dict):
    """
    Checks that the variable, var_name, as the attributes (and values)
    in the att_dict.

    """
    if not isinstance(ds, netCDF4.Dataset):
        ds = netCDF4.Dataset(ds)

    for key, val in att_dict.items():
        try:
            if val != getattr(ds.variables[var_name], key):
                return False
        except AttributeError:
            return False
    return True


def test_simple_write():
    grid = two_triangles()

    fname = 'temp.nc'
    with chdir(test_files):
        grid.save_as_netcdf(fname)
        ds = netCDF4.Dataset(fname)
        os.remove(fname)

    # TODO: Could be lots of tests here.
    assert nc_has_variable(ds, 'mesh')
    assert nc_var_has_attr_vals(ds, 'mesh', {
        'cf_role': 'mesh_topology',
        'topology_dimension': 2,
        'long_name': u'Topology data of 2D unstructured mesh'})
    ds.close()


def test_set_mesh_name():
    grid = two_triangles()
    grid.mesh_name = 'mesh_2'

    fname = 'temp.nc'
    with chdir(test_files):
        grid.save_as_netcdf(fname)
        ds = netCDF4.Dataset(fname)
        os.remove(fname)

    assert nc_has_variable(ds, 'mesh_2')
    assert nc_var_has_attr_vals(ds, 'mesh_2', {
        'cf_role': 'mesh_topology',
        'topology_dimension': 2,
        'long_name': u'Topology data of 2D unstructured mesh'})
    assert nc_var_has_attr_vals(ds, 'mesh_2', {
        'cf_role': 'mesh_topology',
        'topology_dimension': 2,
        'long_name': u'Topology data of 2D unstructured mesh',
        'node_coordinates': 'mesh_2_node_lon mesh_2_node_lat'})

    assert nc_has_variable(ds, 'mesh_2_node_lon')
    assert nc_has_variable(ds, 'mesh_2_node_lat')
    assert nc_has_variable(ds, 'mesh_2_face_nodes')
    assert nc_has_variable(ds, 'mesh_2_edge_nodes')

    assert nc_has_dimension(ds, 'mesh_2_num_node')
    assert nc_has_dimension(ds, 'mesh_2_num_edge')
    assert nc_has_dimension(ds, 'mesh_2_num_face')
    assert nc_has_dimension(ds, 'mesh_2_num_vertices')

    assert not nc_var_has_attr(ds, 'mesh_2', 'face_edge_connectivity')
    ds.close()


def test_write_with_depths():
    """Tests writing a netcdf file with depth data."""

    grid = two_triangles()
    grid.mesh_name = 'mesh1'

    # Create a UVar object for the depths:
    depths = UVar('depth', location='node', data=[1.0, 2.0, 3.0, 4.0])
    depths.attributes['units'] = 'm'
    depths.attributes['standard_name'] = 'sea_floor_depth_below_geoid'
    depths.attributes['positive'] = 'down'

    grid.add_data(depths)

    fname = 'temp.nc'
    with chdir(test_files):
        grid.save_as_netcdf(fname)
        ds = netCDF4.Dataset(fname)
        os.remove(fname)

    assert nc_has_variable(ds, 'mesh1')
    assert nc_has_variable(ds, 'depth')
    assert nc_var_has_attr_vals(ds, 'depth', {
        'coordinates': 'mesh1_node_lon mesh1_node_lat',
        'location': 'node',
        'mesh': 'mesh1'})
    ds.close()


def test_write_with_velocities():
    """Tests writing a netcdf file with velocities on the faces."""
    grid = two_triangles()
    grid.mesh_name = 'mesh2'

    # Create a UVar object for u velocity:
    u_vel = UVar('u', location='face', data=[1.0, 2.0])
    u_vel.attributes['units'] = 'm/s'
    u_vel.attributes['standard_name'] = 'eastward_sea_water_velocity'

    grid.add_data(u_vel)

    # Create a UVar object for v velocity:
    v_vel = UVar('v', location='face', data=[3.2, 4.3])
    v_vel.attributes['units'] = 'm/s'
    v_vel.attributes['standard_name'] = 'northward_sea_water_velocity'

    grid.add_data(v_vel)

    # Add coordinates for face data.
    grid.build_face_coordinates()

    fname = 'temp.nc'
    with chdir(test_files):
        grid.save_as_netcdf(fname)
        ds = netCDF4.Dataset(fname)
        os.remove(fname)

    assert nc_has_variable(ds, 'mesh2')
    assert nc_has_variable(ds, 'u')
    assert nc_has_variable(ds, 'v')
    assert nc_var_has_attr_vals(ds, 'u',
                                {'coordinates': 'mesh2_face_lon mesh2_face_lat',
                                 'location': 'face',
                                 'mesh': 'mesh2',
                                 }
                                )
    ds.close()


def test_write_with_edge_data():
    """Tests writing a netcdf file with data on the edges (fluxes, maybe?)."""

    grid = two_triangles()
    grid.mesh_name = 'mesh2'

    # Create a UVar object for fluxes:
    flux = UVar('flux', location='edge', data=[0.0, 0.0, 4.1, 0.0, 5.1, ])
    flux.attributes['units'] = 'm^3/s'
    flux.attributes['long_name'] = 'volume flux between cells'
    flux.attributes['standard_name'] = 'ocean_volume_transport_across_line'

    grid.add_data(flux)

    # Add coordinates for edges.
    grid.build_edge_coordinates()

    fname = 'temp.nc'
    with chdir(test_files):
        grid.save_as_netcdf(fname)
        ds = netCDF4.Dataset(fname)
        os.remove(fname)

    assert nc_has_variable(ds, 'mesh2')
    assert nc_has_variable(ds, 'flux')
    assert nc_var_has_attr_vals(ds, 'flux', {
        'coordinates': 'mesh2_edge_lon mesh2_edge_lat',
        'location': 'edge',
        'units': 'm^3/s',
        'mesh': 'mesh2'})
    assert np.array_equal(ds.variables['mesh2_edge_lon'],
                          grid.edge_coordinates[:, 0])
    assert np.array_equal(ds.variables['mesh2_edge_lat'],
                          grid.edge_coordinates[:, 1])
    ds.close()


def test_write_with_bound_data():
    """
    Tests writing a netcdf file with data on the boundaries
    suitable for boundary conditions, for example fluxes.

    """
    grid = two_triangles()

    # Add the boundary definitions:
    grid.boundaries = [(0, 1),
                       (0, 2),
                       (1, 3),
                       (2, 3)]

    # Create a UVar object for boundary conditions:
    bnds = UVar('bnd_cond', location='boundary', data=[0, 1, 0, 0])
    bnds.attributes['long_name'] = 'model boundary conditions'
    bnds.attributes['flag_values'] = '0 1'
    bnds.attributes['flag_meanings'] = 'no_flow_boundary  open_boundary'

    grid.add_data(bnds)

    fname = 'temp.nc'
    with chdir(test_files):
        grid.save_as_netcdf(fname)
        ds = netCDF4.Dataset(fname)
        os.remove(fname)

    assert nc_has_variable(ds, 'mesh')
    assert nc_has_variable(ds, 'bnd_cond')
    assert nc_var_has_attr_vals(ds, 'mesh', {
        'boundary_node_connectivity': 'mesh_boundary_nodes'})
    assert nc_var_has_attr_vals(ds,
                                'bnd_cond',
                                {'location': 'boundary',
                                 'flag_values': '0 1',
                                 'flag_meanings': 'no_flow_boundary  open_boundary',
                                 'mesh': 'mesh',
                                 })
    # There should be no coordinates attribute or variable for the
    # boundaries as there is no boundaries_coordinates defined.
    assert not nc_has_variable(ds, 'mesh_boundary_lon')
    assert not nc_has_variable(ds, 'mesh_boundary_lat')
    assert not nc_var_has_attr(ds, 'bnd_cond', 'coordinates')
    ds.close()


def test_write_everything():
    """An example with all features enabled, and a less trivial grid."""

    grid = twenty_one_triangles()

    grid.build_edges()
    grid.build_face_face_connectivity()

    grid.build_edge_coordinates()
    grid.build_face_coordinates()
    grid.build_boundary_coordinates()

    # Depth on the nodes.
    depths = UVar('depth', location='node', data=np.linspace(1, 10, 20))
    depths.attributes['units'] = 'm'
    depths.attributes['standard_name'] = 'sea_floor_depth_below_geoid'
    depths.attributes['positive'] = 'down'
    grid.add_data(depths)

    # Create a UVar object for u velocity:
    u_vel = UVar('u', location='face', data=np.sin(np.linspace(3, 12, 21)))
    u_vel.attributes['units'] = 'm/s'
    u_vel.attributes['standard_name'] = 'eastward_sea_water_velocity'

    grid.add_data(u_vel)

    # Create a UVar object for v velocity:
    v_vel = UVar('v', location='face', data=np.sin(np.linspace(12, 15, 21)))
    v_vel.attributes['units'] = 'm/s'
    v_vel.attributes['standard_name'] = 'northward_sea_water_velocity'

    grid.add_data(v_vel)

    # Fluxes on the edges:
    flux = UVar('flux', location='edge', data=np.linspace(1000, 2000, 41))
    flux.attributes['units'] = 'm^3/s'
    flux.attributes['long_name'] = 'volume flux between cells'
    flux.attributes['standard_name'] = 'ocean_volume_transport_across_line'

    grid.add_data(flux)

    # Boundary conditions:
    bounds = np.zeros((19,), dtype=np.uint8)
    bounds[7] = 1
    bnds = UVar('bnd_cond', location='boundary', data=bounds)
    bnds.attributes['long_name'] = 'model boundary conditions'
    bnds.attributes['flag_values'] = '0 1'
    bnds.attributes['flag_meanings'] = 'no_flow_boundary  open_boundary'

    grid.add_data(bnds)

    fname = 'full_example.nc'
    with chdir(test_files):
        grid.save_as_netcdf(fname)
        ds = netCDF4.Dataset(fname)

        # Now the tests:
        assert nc_has_variable(ds, 'mesh')
        assert nc_has_variable(ds, 'depth')
        assert nc_var_has_attr_vals(ds, 'depth', {
            'coordinates': 'mesh_node_lon mesh_node_lat',
            'location': 'node'})
        assert nc_has_variable(ds, 'u')
        assert nc_has_variable(ds, 'v')
        assert nc_var_has_attr_vals(ds, 'u', {
            'coordinates': 'mesh_face_lon mesh_face_lat',
            'location': 'face',
            'mesh': 'mesh'})
        assert nc_var_has_attr_vals(ds, 'v', {
            'coordinates': 'mesh_face_lon mesh_face_lat',
            'location': 'face',
            'mesh': 'mesh'})
        assert nc_has_variable(ds, 'flux')
        assert nc_var_has_attr_vals(ds, 'flux', {
            'coordinates': 'mesh_edge_lon mesh_edge_lat',
            'location': 'edge',
            'units': 'm^3/s',
            'mesh': 'mesh'})
        assert nc_has_variable(ds, 'mesh')
        assert nc_has_variable(ds, 'bnd_cond')
        assert nc_var_has_attr_vals(ds, 'mesh', {
            'boundary_node_connectivity': 'mesh_boundary_nodes'})
        assert nc_var_has_attr_vals(ds, 'bnd_cond', {
            'location': 'boundary',
            'flag_values': '0 1',
            'flag_meanings': 'no_flow_boundary  open_boundary',
            'mesh': 'mesh'})
        ds.close()

        # And make sure pyugrid can reload it!
        with chdir(test_files):
            grid = UGrid.from_ncfile('full_example.nc', load_data=True)
        # And that some things are the same.
        # NOTE: more testing might be good here.
        # maybe some grid comparison functions?

        assert grid.mesh_name == 'mesh'
        assert len(grid.nodes) == 20

        depth = grid.data['depth']
        assert depth.attributes['units'] == 'm'

        u = grid.data['u']
        assert u.attributes['units'] == 'm/s'

        os.remove(fname)


if __name__ == "__main__":
    test_simple_write()
    test_set_mesh_name()
    test_write_with_depths()
    test_write_with_velocities()
    test_write_with_edge_data()
