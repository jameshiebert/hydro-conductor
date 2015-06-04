''' cells.py

    This module captures the conceptual components of the VIC grid cell,
    broken into classes by elevation band and Hydrological Response Unit (HRU).
    It also provides functions that operate on these class objects, nested
    within the OrderedDict of VIC cells. 

'''

import bisect

class Band(object):
    """ Class capturing vegetation parameters at the elevation band level
    """
# NOTE: can we make glacier_id and open_ground_id global and visible within this class?
    def __init__(self, median_elev, glacier_id, open_ground_id):
    #def __init__(self, area_frac, median_elev):
        self.median_elev = median_elev
        self.hrus = []
        self.glacier_id = glacier_id
        self.open_ground_id = open_ground_id
    @property
    def num_hrus(self):
        return len(self.hrus)
    @property
    def area_frac(self): 
        """ The Band area fraction, equal to the sum of HRU area fractions within this band, 
            which should be equal to the total area fraction of the band as given in the 
            Snow Band Parameters file
        """
        return sum([hru.area_frac for hru in self.hrus])
    @property
    def area_frac_glacier(self):
        return sum([hru.area_frac for hru in self.hrus if hru.veg_type == self.glacier_id])
    @property
    def area_frac_non_glacier(self):
        return self.area_frac - self.area_frac_glacier
    @property
    def area_frac_open_ground(self):
        return sum([hru.area_frac for hru in self.hrus if hru.veg_type == self.open_ground_id])

def create_band(cells, cell_id, elevation, band_size, band_map, glacier_id, open_ground_id):
    """ Creates a new elevation band of glacier vegetation type for a cell with an 
        initial median elevation.
        New bands can only occur on the upper end of the existing set, taking the
        place of zero pads that were provided in the Snow Band Parameters File.
    """
    band_lower_bound = int(elevation - elevation % band_size)
    bisect.insort_left(band_map[cell_id], band_lower_bound)
    # Remove zero pad to left or right of new band. If none exists, throw an exception
    band_idx = band_map[cell_id].index(band_lower_bound)
    if(0 in band_map[cell_id][0:band_idx+1]): # this was appended to the lower end of valid bands
        band_map[cell_id].remove(0) # removes a 0 left of the new entry
    elif(0 in band_map[cell_id][band_idx+1:band_idx+2]): # this was appended to the upper end of valid bands
        del band_map[cell_id][band_idx+1] # removes the first 0 right of the new entry
    else: # there's no zero pad available for this new band
        raise LookupError ('create_band: Attempted to create a new elevation band at {}m \
            (RGM output DEM pixel elevation at {}) in cell {}, but ran out of available slots. \
            Increase number of 0 pads in the VIC Snow Band Parameters file and re-run. Exiting.\
            \n'.format(band_lower_bound, elevation, cell_id))
        sys.exit(0)
    # Get final index / id of Band after zero pad removed from band_map
    band_idx = band_map[cell_id].index(band_lower_bound)
    # Create an additional Band object in the cell with initial median elevation
    cells[cell_id][str(band_idx)] = Band(elevation, glacier_id, open_ground_id)
    return band_idx

def delete_band(cells, cell_id, band_lower_bound, band_map):
    """ Removes the band starting at band_lower_bound from the given cell 
        and sets its position in band_map to a zero pad
    """
    band_idx = band_map[cell_id].index(band_lower_bound)
    del cells[cell_id][str(band_idx)]
    band_map[cell_id][band_idx] = 0

class HydroResponseUnit(object):
    """ Class capturing vegetation parameters at the single vegetation tile (HRU) level 
        (of which there can be many per band)
    """
    def __init__(self, veg_type, area_frac, root_zone_parms):
        self.veg_type = veg_type
        self.area_frac = area_frac
        self.root_zone_parms = root_zone_parms

def create_hru(cells, cell_id, band_id, veg_type, area_frac, root_zone_parms):
    """ Creates a new HRU of veg_type within a given cell and Band
    """
    new_hru = HydroResponseUnit(veg_type, area_frac, root_zone_parms)
    # Append new_hru to existing list of HRUs for this band, and re-sort the list ascending by veg_type
    cells[cell_id][band_id].hrus.append(new_hru)
    cells[cell_id][band_id].hrus.sort(key=lambda x: x.veg_type)

def delete_hru(cells, cell_id, band_id, veg_type):
    """ Deletes an HRU of veg_type within a given cell and Band
    """
    for hru_idx, hru in enumerate(cells[cell_id][band_id].hrus):
        if hru.veg_type == veg_type:
            del cells[cell_id][band_id].hrus[hru_idx]
            break # there will only ever be one tile of any given vegetation type

def update_area_fracs(cells, cell_areas, num_snow_bands, band_size, band_map, pixel_to_cell_map,
                      surf_dem, num_rows_dem, num_cols_dem, glacier_mask, glacier_id, open_ground_id):
    """ Calculates and updates the area fractions of elevation bands within VIC cells, and
        area fraction of glacier and open ground within VIC cells (broken down by elevation band).
        Calls VegParams::update_tiles() to update all vegetation parameter tiles (or add/delete them as needed)
    """
    all_pixel_elevs = {} # temporarily store pixel elevations in bins by band so the median can be calculated
    band_areas = {} # temporary count of pixels, a proxy for area, within each band
    glacier_areas = {} # temporary count of pixels landing within the glacier mask, a proxy for glacier area
    for cell in cells:
        all_pixel_elevs[cell] = [] * num_snow_bands
        band_areas[cell] = [0] * num_snow_bands
        glacier_areas[cell] = [0] * num_snow_bands
    for row in range(num_rows_dem):
        for col in range(num_cols_dem):
            cell = pixel_to_cell_map[row][col][0] # get the VIC cell this pixel belongs to
            if cell != 'NA':
                # Use the RGM DEM output to update the pixel median elevation in the pixel_to_cell_map
                pixel_elev = float(surf_dem[row][col])
                pixel_to_cell_map[row][col][1] = pixel_elev
                for band_idx, band in enumerate(band_map[cell]):
                    band_found = False
                    if (band < pixel_elev) and (pixel_elev < (band + band_size)):
                        band_found = True
                        # Gather all pixel_elev values to update the median_elev of this band later
                        all_pixel_elevs[cell][band_idx].append(pixel_elev)
                        band_areas[cell][band_idx] += 1
                        if glacier_mask[row][col]:
                            glacier_areas[cell][band_idx] += 1
                        break
                if not band_found: # we have to introduce a new elevation band
                    new_band_idx = create_band(cells, cell, pixel_elev, band_size, band_map, glacier_id, open_ground_id)
                    all_pixel_elevs[cell][new_band_idx].append(pixel_elev)
                    band_areas[cell][new_band_idx] += 1
                    if glacier_mask[row][col]:
                        glacier_areas[cell][new_band_idx] += 1
                        break
    # NOTE: should we check if any pixels with 0 elevation (RGM error?) are dropped 
    # into a 0-pad (invalid / nonexistent) band (since band_map will have 0 pads)?

    # Update all band median elevations for all cells, delete unused Bands
    for cell in cells:
        for band_idx, band_lower_bound in enumerate(band_map[cell]):
            cells[cell][band_idx].median_elev = np.median(all_pixel_elevs[cell][band_idx])
            # if no entries exist for this band in all_pixel_elevs, delete the band
            if not all_pixel_elevs[cell][band_idx]:
                delete_band(cells, cell, band_lower_bound, band_map)

    # Update all Band and HRU area fractions in all cells
    for cell in cells:
        for band_idx, band in enumerate(band_map[cell]):
            band_idx = str(band_idx)
            # Update area fraction for this Band
            new_band_area_frac = float(band_areas[cell][band_idx]) / cell_areas[cell]
            new_glacier_area_frac = float(glacier_areas[cell][band_idx]) / cell_areas[cell]
            # If the glacier HRU area fraction has changed for this band then we need to update all area fractions
            if new_glacier_area_frac != cells[cell][band_idx].area_frac_glacier:
                if new_glacier_area_frac < 0:
                    print('update_band_area_fracs(): Error: Calculated a negative glacier area fraction for cell {}, band {}. Exiting.\n'.format(cell, band))
                    sys.exit(0)
                # Calculate new non-glacier area fraction for this band
                new_non_glacier_area_frac = new_band_area_frac - new_glacier_area_frac
                # Calculate new_residual area fraction
                new_residual_area_frac = new_non_glacier_area_frac - cells[cell][band_idx].area_frac_non_glacier
# NOTE: what should be done here for Bands just created above?  cells[cell][band_idx].area_frac_non_glacier = 0 & cells[cell][band_idx].area_frac_open_ground = 1 ?
                # Calculate new open ground area fraction
                new_open_ground_area_frac = np.max([0, (cells[cell][band_idx].area_frac_open_ground + new_residual_area_frac)])
                
                # Use old proportions of vegetated areas for scaling their area fractions in this iteration
                veg_scaling_divisor = cells[cell][band_idx].area_frac_non_glacier - cells[cell][band_idx].area_frac_open_ground
                # Calculate the change in sum of vegetated area fractions
                delta_area_vegetated = np.min([0, (cells[cell][band_idx].area_frac_open_ground + new_residual_area_frac)])

                # Update area fractions for all HRUs in this Band  
                glacier_found = False
                open_ground_found = False
                for hru_idx, hru in enumerate(cells[cell][band_idx].hrus):
                    if hru.veg_type == glacier_id:
                        glacier_found = True
                        cells[cell][band_idx].hrus[hru_idx].area_frac = new_glacier_area_frac
                    if hru.veg_type == open_ground_id:
                        open_ground_found = True
                        # If open ground area fraction was reduced to 0, we delete the HRU
                        if new_open_ground_area_frac == 0:
                            delete_hru(cells, cell, band_idx, open_ground_id)
                        else:
                            cells[cell][band_idx].hrus[hru_idx].area_frac = new_open_ground_area_frac
                    else:
                        # Calculate change in HRU area fraction & update
                        delta_area_hru = delta_area_vegetated * (cells[cell][band_idx].hrus[hru_idx].area_frac / veg_scaling_divisor)
                        new_hru_area_frac = cells[cell][band_id].hrus[hru_idx].area_frac + delta_area_hru
                        if new_hru_area_frac <= 0: # HRU has disappeared, never to return (only open ground can come back in its place)
                            delete_hru(cell, band_idx, cells[cell][band_idx].hrus[hru_idx])
                        else:
                            cells[cell][band_idx].hrus[hru_idx].area_frac = new_hru_area_frac
                # Create glacier HRU if it didn't already exist, if we have a non-zero new_glacier_area_frac. 
                # If glacier area fraction was reduced to 0, we leave the "shadow glacier" HRU in place for VIC
                if not glacier_found and (new_glacier_area_frac > 0):
                    create_hru(cells, cell, band, glacier_id, new_glacier_area_frac, glacier_root_zone_parms)
                # If open ground was exposed in this band we need to add an open ground HRU
                if not open_ground_found and (new_open_ground_area_frac > 0):
                    create_hru(cells, cell, band, open_ground_id, new_open_ground_area_frac, open_ground_root_zone_parms)

                # Sanity check that glacier + non-glacier area fractions add up to Band's total area fraction, within tolerance
                sum_test = new_glacier_area_frac + new_non_glacier_area_frac
                if not np.allclose([sum_test], [new_band_area_frac]): # default rtol=1e-5, atol=1e-8
                    print('Error: update_band_area_fracs: cell {}, band {}: glacier area fraction {} + non-glacier area fraction {} = {} \
                        is not equal to the band area fraction of {}'.format(cell, band, new_glacier_area_frac, new_non_glacier_area_frac, \
                            sum_test, new_band_area_frac))
                    sys.exit(0)
