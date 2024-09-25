from shapely.geometry import Polygon, box
from esa_snappy import ProductIO, GPF, jpy
import esa_snappy
from glob import iglob
from os.path import join
import matplotlib.pyplot as plt

# Ensure that the GPF is initialized
GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()

# Define product path and get input files
product_path = 'F:\\xBD\\Kaharamanmaras SAR\\04'
output_path = 'D:\\xBD\\Kaharamanmaras SAR\\04\\SNAPPY'

input_S1_files = sorted(list(iglob(join(product_path, '**', '*S1*.zip'), recursive=True)))

# Initialize lists for metadata
name, sensing_mode, product_type, polarization, height, width, band_names = ([] for i in range(7))

# Read products and extract metadata
S1_data = []
for file in input_S1_files:
    S1_read = ProductIO.readProduct(file)
    name.append(S1_read.getName())
    sensing_mode.append(file.split("_")[3])
    product_type.append(file.split("_")[4])
    polarization.append(file.split("_")[-6])
    height.append(S1_read.getSceneRasterHeight())
    width.append(S1_read.getSceneRasterWidth())
    band_names.append(S1_read.getBandNames())
    S1_data.append(S1_read)

# Functions to read and write products
def read(filename):
    return ProductIO.readProduct(filename)

def write(product, filename, format="BEAM-DIMAP"):
    ProductIO.writeProduct(product, filename, format)

# Subset function
wkt_PO = 'POLYGON((36.8412 37.5383, 36.8412 37.6003, 36.9932 37.6003, 36.9932 37.5383, 36.8412 37.5383))'
geom_PO = esa_snappy.WKTReader().read(wkt_PO)

def subset(product, geom):
    parameters = esa_snappy.HashMap()
    parameters.put('geoRegion', geom)
    parameters.put('copyMetadata', True)
    return GPF.createProduct('Subset', parameters, product)

# Apply Orbit File
def apply_orbit_file(product):
    parameters = esa_snappy.HashMap()
    parameters.put('Apply-Orbit-File', True)
    return GPF.createProduct('Apply-Orbit-File', parameters, product)

# TOPSAR Split
def topsar_split(product, subswath):
    parameters = esa_snappy.HashMap()
    parameters.put('subswath', subswath)
    parameters.put('selectedPolarisations', 'VV,VH')
    return GPF.createProduct('TOPSAR-Split', parameters, product)

# Back Geocoding
def back_geocoding(pairs):
    parameters = esa_snappy.HashMap()
    parameters.put('demName', 'SRTM 1Sec HGT')
    parameters.put('demResamplingMethod', 'BILINEAR_INTERPOLATION')
    parameters.put('resamplingType', 'BILINEAR_INTERPOLATION')
    parameters.put('maskOutAreaWithoutElevation', True)
    parameters.put('outputDerampDemodPhase', False)
    return GPF.createProduct('Back-Geocoding', parameters,pairs )


# Coherence
def coherence(product):
    parameters = esa_snappy.HashMap()
    Integer = jpy.get_type('java.lang.Integer')
    parameters.put('cohWinAz', Integer(3))
    parameters.put('cohWinRg', Integer(10))
    parameters.put('squarePixel', True)
    return GPF.createProduct('Coherence', parameters, product)


# SAR preprocessing workflow
def sar_preprocessing_workflow(collection, output_dir):
    pre_list = []
    for i, product in enumerate(collection):
        orbit_applied = apply_orbit_file(product)
        filename = join(output_dir, f"orbit_applied_{i}.dim")
        write(orbit_applied, filename)
        pre_list.append(read(filename))
    return pre_list

# Process the data
PL = sar_preprocessing_workflow(S1_data, output_path)

# TOPSAR split each product for each subswath
subswaths = ['IW1', 'IW2', 'IW3']
split_products = {subswath: [] for subswath in subswaths}

# Apply the split only for subswath 2
for subswath in subswaths:
    if subswath == 'IW2':
        for i, product in enumerate(PL):
            split = topsar_split(product, subswath)
            filename = join(output_path, f"split_{subswath}_{i}.dim")
            write(split, filename)
            split_products[subswath].append(read(filename))



# Define the specific pairs for processing
product_pairs_1 = {
    'I13': [(split_products['IW1'][0], split_products['IW1'][1])],
}
product_pairs_2 = {
    'IW2': [(split_products['IW2'][0], split_products['IW2'][1])],
}
product_pairs_3 = {
    'IW3': [(split_products['IW3'][0], split_products['IW3'][1])],
}


# Function to process product pairs
def process_back_geocoding(product_pairs, output_path):
    BGC_results = {}
    for subswath, pairs in product_pairs.items():
        BGC_results[subswath] = []
        for idx, pair in enumerate(pairs):
            BGC = back_geocoding(pair)
            filename_BGC = join(output_path, f"BGC_{subswath}_{idx}.dim")
            write(BGC, filename_BGC)
            BGC_results[subswath].append(read(filename_BGC))
    return BGC_results

# Perform back-geocoding and save results
#BGC_1 = process_back_geocoding(product_pairs_1, output_path)
BGC_2 = process_back_geocoding(product_pairs_2, output_path)
#BGC_3 = process_back_geocoding(product_pairs_3, output_path)



subset_product = subset(BGC_2, geom_PO)


Coherence01= coherence(subset_product)

ProductIO.writeProduct(Coherence01, 'E:\\xBD\\Kaharamanmaras SAR\\01\\SNAPPY\\coherence01.dim',"BEAM-DIMAP")
