import cardoon
import json
import glob
import os

def package_analyses(search_paths, output_dir):
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    for path in search_paths:
        for filename in glob.glob(os.path.join(path, "*.json")):
            analysis = cardoon.load(filename)
            with open(os.path.join(output_dir, os.path.basename(filename)), 'w') as f:
                json.dump(analysis, f)

if __name__ == "__main__":
    package_analyses(["../analysis"], "packaged")
