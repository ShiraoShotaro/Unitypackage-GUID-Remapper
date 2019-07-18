#!/usr/bin/env python
# -*- coding:UTF-8 -*-
# Copyright (c) 2019 Shirao Shotaro.
# This code is published under MIT-LISENCE.
import sys
import tarfile
import os
import shutil
import hashlib
import time
import yaml
from collections import OrderedDict

TEMPORARY_FOLDER_PATH = 'tmp'

def iterateDict(ymlobj: dict, hash_table: dict, upack_fpath: str, replaced_count: int, warning_count: int):
    for key in ymlobj:
        replaced_count, warning_count = replaceGUID(ymlobj, key, hash_table, upack_fpath, replaced_count, warning_count)
        warning_count = isUnicodeStr(ymlobj[key], upack_fpath, warning_count)
    return replaced_count, warning_count


def iterateList(ymlobj: list, hash_table: dict, upack_fpath: str, replaced_count: int, warning_count: int):
    for key in range(0, len(ymlobj)):
        replaced_count, warning_count = replaceGUID(ymlobj, key, hash_table, upack_fpath, replaced_count, warning_count)
        warning_count = isUnicodeStr(ymlobj[key], upack_fpath, warning_count)
    return replaced_count, warning_count


def isUnicodeStr(value, upack_fpath: str, warning_count: int):
    if type(value) is str:
        try:
            value.encode().decode('ascii')
        except UnicodeDecodeError:
            printf('Unicode string has included. string = ' + value, upack_fpath)
            warning_count += 1

    return warning_count


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
    print(os.path.basename(filepath) + ' > ' + string)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('No file input.')
        print('Usage: Unitypackage-GUID-Remapper.exe [unitypackage filepath] ...')
        print('You can drag input unitypackage(s) and drop to this exe file on Windows GUI.')
        exit(-1)

    warning_count = 0

    if os.path.exists(TEMPORARY_FOLDER_PATH):
        shutil.rmtree(TEMPORARY_FOLDER_PATH)

    for upack_fpath in sys.argv[1:]:
        printf('start.', upack_fpath)

        # temporary folder
        os.makedirs(TEMPORARY_FOLDER_PATH)

        # open tar
        with tarfile.open(upack_fpath, 'r:gz') as tar:
            printf(str(len(tar.getnames())) + ' file(s) are included.', upack_fpath)

            # extract tar
            tar.extractall('tmp/')

        # フォルダ名からhashテーブルを作成
        folders = os.listdir(TEMPORARY_FOLDER_PATH)
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
            os.rename(TEMPORARY_FOLDER_PATH + '/' + dirn, TEMPORARY_FOLDER_PATH + '/' + hash_table[dirn])

        printf('Renamed all directories.', upack_fpath)

        # メタファイルから該当するGUIDを探していく
        for dirn in hash_table:
            with open(TEMPORARY_FOLDER_PATH + '/' + hash_table[dirn] + '/pathname', 'r') as pn:
                printf('check meta = ' + pn.read() + ' (' + hash_table[dirn] + ')', upack_fpath)

            meta = None
            with open(TEMPORARY_FOLDER_PATH + '/' + hash_table[dirn] + '/asset.meta', 'r') as yaml_file:
                meta = yaml.safe_load(yaml_file)

            okcount, wcount = iterateDict(meta, hash_table, upack_fpath, 0, 0)

            # yamlを置きなおす
            """
            with open(TEMPORARY_FOLDER_PATH + '/' + hash_table[dirn] + '/asset.meta', 'w') as yaml_file:
                # yaml_file.write(yaml.dump(meta, default_flow_style=False))
                yaml_file.write(yaml.dump(meta))

            printf('replaced = ' + str(okcount) + ' / warning count = ' + str(wcount) +
                   ' (warning total = ' + str(warning_count + wcount) + ')', upack_fpath)
            warning_count += wcount
            """

        # ファイル名の作成
        folder_path, file_name = os.path.split(upack_fpath)
        file_name, file_ext = os.path.splitext(file_name)

        tar_filepath = folder_path + '/' + file_name + '_remapped' + file_ext
        printf('packaging to = ' + tar_filepath, upack_fpath)

        input()

        os.chdir(TEMPORARY_FOLDER_PATH)
        with tarfile.open('../' + tar_filepath, 'w:gz') as tar:
            for dirn in hash_table:
                tar.add(hash_table[dirn])

        printf('Finished. Total warnings = ' + str(warning_count), upack_fpath)
        input()
        os.chdir('../')

    shutil.rmtree(TEMPORARY_FOLDER_PATH)
