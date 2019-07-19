#!/usr/bin/env python
# -*- coding:UTF-8 -*-
# Copyright (c) 2019 Shirao Shotaro.
# This code is published under MIT-LISENCE.
import sys
import argparse
import os
import tarfile
import shutil
import hashlib
import time
import tempfile
from pathlib import Path


def replaceGUID(infile_path: str, rewrite_table: dict):
    import copy
    infile = None
    try:
        with open(infile_path, 'rt') as f:
            infile = f.read()
        outfile = copy.deepcopy(infile)
        for from_guid in rewrite_table.keys():
            outfile = outfile.replace(from_guid, rewrite_table[from_guid])
        if(infile is not outfile):
            with open(infile_path, 'wt') as f:
                f.write(outfile)
    except UnicodeDecodeError:
        return


def printf(string: str, filepath: str):
    print(os.path.basename(filepath) + ' > ' + string, file=sys.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Remap assets GUID in a unitypackage with holding dependency.")
    parser.add_argument('unitypackage',
                        nargs='+',
                        type=str)
    args = parser.parse_args()

    warning_count = 0
    base_dir = os.getcwd()

    for upack_fpath in args.unitypackage:
        upack_fpath = Path(upack_fpath).resolve()
        # temporary folder
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            printf('start.', upack_fpath)

            # open tar
            with tarfile.open(upack_fpath, 'r:gz') as tar:
                printf(str(len(tar.getnames())) + ' file(s) are included.', upack_fpath)

                # extract tar
                tar.extractall()

            # フォルダ名からhashテーブルを作成
            folders = os.listdir()
            hash_table = {}

            while True:
                for dirn in folders:
                    if os.path.isdir(dirn):
                        hash_table[dirn] = hashlib.md5((dirn + str(time.time())).encode()).hexdigest()
                        printf('entity = ' + dirn + ' => ' + hash_table[dirn], upack_fpath)
                    else:
                        printf('!!! INVALID UNITYPACKAGE ERROR !!!', upack_fpath)
                        raise RuntimeError('Invalid unitypackage.')
                if (len(hash_table) * 2) == len(set(list(hash_table.values()) + list(hash_table.keys()))):
                    break
                else:
                    printf('Hash collision occured. Retry hash.', upack_fpath)

            printf('Hash calcuration has been completed.', upack_fpath)

            # フォルダ名を変更
            for dirn in hash_table:
                os.rename(tmpdir + '/' + dirn, tmpdir + '/' + hash_table[dirn])

            printf('Renamed all directories.', upack_fpath)

            # メタファイルから該当するGUIDを探していく
            for target in Path('.').glob('**/asset'):
                replaceGUID(target, hash_table)
            for target in Path('.').glob('**/asset.meta'):
                replaceGUID(target, hash_table)

            # ファイル名の作成
            folder_path, file_name = os.path.split(upack_fpath)
            file_name, file_ext = os.path.splitext(file_name)

            tar_filepath = 'archtemp.tar'
            printf('packaging to = ' + tar_filepath, upack_fpath)

            with tarfile.open(folder_path + '/' + tar_filepath, 'w:gz') as tar:
                for dirn in hash_table:
                    tar.add(hash_table[dirn])

            shutil.move(folder_path + '/' + tar_filepath, folder_path + '/' + file_name + '_REAMAPPED' + file_ext)

            os.chdir(base_dir)
            printf('Finished. Total warnings = ' + str(warning_count), upack_fpath)
