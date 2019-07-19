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
import yaml
import tempfile
from collections import OrderedDict


def iterateDict(ymlobj: dict, hash_table: dict, upack_fpath: str, replaced_count: int, warning_count: int):
    for key in ymlobj:
        replaced_count, warning_count = replaceGUID(ymlobj, key, hash_table, upack_fpath, replaced_count, warning_count)
    return replaced_count, warning_count


def iterateList(ymlobj: list, hash_table: dict, upack_fpath: str, replaced_count: int, warning_count: int):
    for key in range(0, len(ymlobj)):
        replaced_count, warning_count = replaceGUID(ymlobj, key, hash_table, upack_fpath, replaced_count, warning_count)
    return replaced_count, warning_count


def replaceGUID(ymlobj, key, hash_table: dict, upack_fpath: str, replaced_count: int, warning_count: int):
    if key == 'guid':
        if ymlobj[key] in hash_table:
            ymlobj[key] = hash_table[ymlobj[key]]
            replaced_count += 1
        else:
            printf('This object is depending on MISSING assets. GUID = ' + ymlobj[key], upack_fpath)
            warning_count += 1

    elif isinstance(ymlobj[key], dict):
        replaced_count, warning_count = iterateDict(
            ymlobj[key], hash_table, upack_fpath, replaced_count, warning_count)
        pass
    elif isinstance(ymlobj[key], tuple) or isinstance(ymlobj[key], list):
        replaced_count, warning_count = iterateList(
            ymlobj[key], hash_table, upack_fpath, replaced_count, warning_count)
        pass

    return replaced_count, warning_count


def printf(string: str, filepath: str):
    print(os.path.basename(filepath) + ' > ' + string, file=sys.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Remap assets GUID in a unitypackage with holding dependency.")
    parser.add_argument('unitypackage',
                        nargs='+',
                        type=str)
    args = parser.parse_args()

    warning_count = 0

    for upack_fpath in args.unitypackage:

        # temporary folder
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            upack_fpath = os.path.realpath(upack_fpath)
            printf('start.', upack_fpath)

            # open tar
            with tarfile.open(upack_fpath, 'r:gz') as tar:
                printf(str(len(tar.getnames())) + ' file(s) are included.', upack_fpath)

                # extract tar
                tar.extractall(tmpdir)

            # フォルダ名からhashテーブルを作成
            folders = os.listdir(tmpdir)
            hash_table = {}
            while True:
                for dirn in folders:
                    if not os.path.isdir(dirn):
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
            for dirn in hash_table:
                with open(tmpdir + '/' + hash_table[dirn] + '/pathname', 'r') as pn:
                    printf('check meta = ' + pn.read() + ' (' + hash_table[dirn] + ')', upack_fpath)

                meta = None
                with open(tmpdir + '/' + hash_table[dirn] + '/asset.meta', 'r') as yaml_file:
                    meta = yaml.safe_load(yaml_file)

                okcount, wcount = iterateDict(meta, hash_table, upack_fpath, 0, 0)

                # yamlを置きなおす
                with open(tmpdir + '/' + hash_table[dirn] + '/asset.meta', 'w') as yaml_file:
                    # yaml_file.write(yaml.dump(meta, default_flow_style=False))
                    yaml_file.write(yaml.dump(meta))

                printf('replaced = ' + str(okcount) + ' / warning count = ' + str(wcount) +
                       ' (warning total = ' + str(warning_count + wcount) + ')', upack_fpath)
                warning_count += wcount

            # ファイル名の作成
            folder_path, file_name = os.path.split(upack_fpath)
            file_name, file_ext = os.path.splitext(file_name)

            tar_filepath = 'archtemp.tar'
            printf('packaging to = ' + tar_filepath, upack_fpath)

            with tarfile.open(folder_path + '/' + tar_filepath, 'w:gz') as tar:
                for dirn in hash_table:
                    tar.add(hash_table[dirn])

            shutil.move(folder_path + '/' + tar_filepath, folder_path + '/' + file_name + '_REAMAPPED' + file_ext)

            os.chdir(tempfile.gettempdir())
            printf('Finished. Total warnings = ' + str(warning_count), upack_fpath)
