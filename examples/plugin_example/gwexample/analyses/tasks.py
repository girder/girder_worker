from girder_worker.app import app
from girder_worker_utils import types
from girder_worker_utils.decorators import argument


@app.task
@argument('n', types.Integer, min=1)
def fibonacci(n):
    """Compute the nth fibonacci number recursively."""
    if n == 1 or n == 2:
        return 1
    return fibonacci(n-1) + fibonacci(n-2)

@app.task
# @argument('image_name', 'slide_name', 'path')
def nuclei(image_name, slide_name, path):
    "running nuclei"
    print(app, '++++++++++')
    if path:
        print('using arg path !!')
        os.chdir(path)
    else:
        print('using default path !!')
        os.chdir('/home/rc-svc-pinaki.sarder-web/digital_slide_archive/devops/singularity-minimal')
    print('Current Path => ', os.getcwd())
    path = os.getcwd()
    flags = os.O_RDWR | os.O_CREAT
    sif_image = os.open('sarderlab_histomicstk_latest.sif', flags)
    sif_image_path = path + image_name if image_name else '/sarderlab_histomicstk_latest.sif'
    slide_image = os.open(slide_name, flags)
    slide_image_path = path + slide_name if slide_name else '18-142_PAS_1of6.svs'
    output = os.open('Nuclei-outputNucleiAnnotationFile.anot', flags)
    output_path = path + '/Nuclei-outputNucleiAnnotationFile.anot'
    run_container = f'apptainer run --pwd /HistomicsTK/histomicstk/cli {sif_image} NucleiDetection {slide_image} {output}'
    try:
        res = subprocess.call(f'apptainer run --pwd /HistomicsTK/histomicstk/cli {sif_image_path} NucleiDetection {slide_image_path} {output_path}', shell=True, bufsize=0,stdin=subprocess.PIPE,stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="UTF8")
        print(res, '----1')

    except Exception as e:
        print(f"Exception occured {e}")

