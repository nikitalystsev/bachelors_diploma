#!/bin/bash

set -e
cd "$(dirname "$0")"

#make -f iu7-nir-student.mk delete_report
make -f iu7-nir-student.mk delete_prez
#make -f iu7-nir-student.mk release/report.pdf
make -f iu7-nir-student.mk release/slides.pdf
#make -f iu7-nir-student.mk

REPORT="release/report.pdf"
PREZ="release/slides.pdf"

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    yandex-browser "$REPORT" >/dev/null 2>&1 &
    yandex-browser "$PREZ" >/dev/null 2>&1 &
elif [[ "$OSTYPE" == "darwin"* ]]; then
    for app in "Yandex" "Yandex Browser" "Яндекс Браузер" "Яндекс"; do
#        if open -a "$app" "$REPORT" >/dev/null 2>&1; then
#            exit 0
#        fi
        if open -a "$app" "$PREZ" >/dev/null 2>&1; then
            exit 0
        fi
#        if open -a "$app" "$REPORT" "$PREZ" >/dev/null 2>&1; then
#            exit 0
#        fi
    done

    echo "Yandex Browser not found. Opening with the default PDF viewer: $REPORT $PREZ"
    open "$REPORT"
    open "$PREZ"
elif [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "cygwin"* || "${OS:-}" == "Windows_NT" ]]; then
    YANDEX_BROWSER="$(cygpath -u "C:\\Users\\user\\AppData\\Local\\Yandex\\YandexBrowser\\Application\\browser.exe")"
    REPORT_URL="file:///$(cygpath -am "$REPORT")"
    PREZ_URL="file:///$(cygpath -am "$PREZ")"

    "$YANDEX_BROWSER" "$REPORT_URL" >/dev/null 2>&1 &
    "$YANDEX_BROWSER" "$PREZ_URL" >/dev/null 2>&1 &
else
    echo "Unsupported OS. PDF built: $REPORT $PREZ"
fi
