#!/bin/bash

set -e
cd "$(dirname "$0")"

make -f iu7-nir-student.mk delete_report
make -f iu7-nir-student.mk

yandex-browser release/report.pdf
