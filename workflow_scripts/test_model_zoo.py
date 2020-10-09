import argparse
import onnx
import os
from pathlib import Path
import subprocess
import sys
import time

cwd_path = Path.cwd()

def run_lfs_install():
    result = subprocess.run(['git', 'lfs', 'install'], cwd=cwd_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print('Git LFS install completed with return code= {}'.format(result.returncode))

def pull_lfs_file(file_name):
    result = subprocess.run(['git', 'lfs', 'pull', '--include', file_name, '--exclude', '\'\''], cwd=cwd_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print('LFS pull completed with return code= {}'.format(result.returncode))

def main():
    parser = argparse.ArgumentParser(description='Test settings')
    # default: test all models in the repo
    # if test_dir is specified, only test files under that specified path
    parser.add_argument('--test_dir', required=False, default='', type=str, 
                        help='Directory path for testing. e.g., text, vision')
    args = parser.parse_args()
    parent_dir = []
    # if not set, go throught each directory
    if not args.test_dir:
        for file in os.listdir():
            if os.path.isdir(file):
                parent_dir.append(file)
    else:
        parent_dir.append(args.test_dir)
    model_list = []
    for directory in parent_dir:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.onnx'):
                    onnx_model_path = os.path.join(root, file)
                    model_list.append(onnx_model_path)
                    print(onnx_model_path)

    # run lfs install before starting the tests
    run_lfs_install()

    print('=== Running ONNX Checker on {} models ==='.format(len(model_list)))
    # run checker on each model
    failed_models = []
    for model_path in model_list:
        start = time.time()
        model_name = model_path.split('/')[-1]
        print('-----------------Testing: {}-----------------'.format(model_name))
        try:
            pull_lfs_file(model_path)
            
            # check original inferred
            model = onnx.load(model_path)
            onnx.checker.check_model(model)
            # stricter onnx.checker with onnx.shape_inference
            onnx.checker.check_model(model, True)

            # check inferred model as well
            inferred_model = onnx.shape_inference.infer_shapes(model)
            onnx.checker.check_model(inferred_model)
            onnx.checker.check_model(inferred_model, True)
            # remove the model to save space in CIs
            os.remove(model_path)

            print('[PASS]: {} is checked by onnx. '.format(model_name))

        except Exception as e:
            print('[FAIL]: {}'.format(e))
            failed_models.append(model_path)
        end = time.time()
        print('--------------Time used: {} secs-------------'.format(end - start))


    if len(failed_models) == 0:
        print('{} models have been checked.'.format(len(model_list)))
    else:
        print('In all {} models, {} models failed.'.format(len(model_list), len(failed_models)))
        sys.exit(1)
      

if __name__ == '__main__':
    main()