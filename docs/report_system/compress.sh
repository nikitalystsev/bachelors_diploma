#!/usr/bin/env bash
# (c) Alexander Kostritsky 2024
# Жулик, не воруй мои скрептосы
# Ну ладно, немножко можешь
# Я их тоже свiрiвiв

usage() {
    echo "Использование: $0 [--check] <путь_к_папке>"
    exit 1
}

# -----------------------------
# Разбор аргументов
# -----------------------------
CHECK_MODE=false
SOURCE_DIR=""

case "${1:-}" in
    --check)
        CHECK_MODE=true
        if [ $# -ne 2 ]; then
            usage
        fi
        SOURCE_DIR="$2"
        ;;
    -h|--help)
        usage
        ;;
    *)
        if [ $# -ne 1 ]; then
            usage
        fi
        SOURCE_DIR="$1"
        ;;
esac

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Ошибка: директория '$SOURCE_DIR' не существует."
    exit 1
fi

# -----------------------------
# Поиск Ghostscript
# -----------------------------
if command -v gs >/dev/null 2>&1; then
    GS_BIN="gs"
elif command -v gswin64c >/dev/null 2>&1; then
    GS_BIN="gswin64c"
elif command -v gswin32c >/dev/null 2>&1; then
    GS_BIN="gswin32c"
else
    echo "Ошибка: Ghostscript не найден. Нужна команда 'gs' или 'gswin64c'."
    exit 1
fi

# -----------------------------
# Portable размер файла:
# macOS/BSD: stat -f%z
# Linux/GNU: stat -c%s
# -----------------------------
get_file_size() {
    local file="$1"
    local size=""

    if size=$(stat -f%z "$file" 2>/dev/null); then
        if [[ "$size" =~ ^[0-9]+$ ]]; then
            printf '%s\n' "$size"
            return 0
        fi
    fi

    if size=$(stat -c%s "$file" 2>/dev/null); then
        if [[ "$size" =~ ^[0-9]+$ ]]; then
            printf '%s\n' "$size"
            return 0
        fi
    fi

    return 1
}

# -----------------------------
# Не затираем старые backup-файлы
# -----------------------------
make_backup_path() {
    local file="$1"
    local candidate="${file}.backup"
    local n=1

    while [ -e "$candidate" ]; do
        candidate="${file}.backup.${n}"
        n=$((n + 1))
    done

    printf '%s\n' "$candidate"
}

# -----------------------------
# Очистка временной директории
# -----------------------------
current_tmp_dir=""

cleanup_current_tmp_dir() {
    if [ -n "${current_tmp_dir:-}" ] && [ -d "$current_tmp_dir" ]; then
        rm -rf "$current_tmp_dir"
    fi
}

trap 'cleanup_current_tmp_dir' EXIT
trap 'cleanup_current_tmp_dir; exit 130' INT
trap 'cleanup_current_tmp_dir; exit 143' TERM

# -----------------------------
# Настройки
# -----------------------------
THRESHOLD_PERCENT=10
MIN_OUTPUT_PERCENT=$((100 - THRESHOLD_PERCENT))

problems_found=false
found_any=false

# MSYS/Git Bash иногда пытается превратить /FlateEncode в путь Windows.
case "$(uname -s)" in
    CYGWIN*|MINGW*|MSYS*)
        COLOR_FILTER="//FlateEncode"
        ;;
    *)
        COLOR_FILTER="/FlateEncode"
        ;;
esac

# -----------------------------
# Основной цикл
# -----------------------------
while IFS= read -r -d '' pdf_file; do
    found_any=true
    echo "Обработка: $pdf_file"

    if ! original_size=$(get_file_size "$pdf_file"); then
        echo "  Ошибка: не удалось определить размер исходного файла."
        problems_found=true
        continue
    fi

    if [ -z "$original_size" ] || [ "$original_size" -eq 0 ]; then
        echo "  Пропуск: размер файла нулевой или не определён."
        problems_found=true
        continue
    fi

    # Временная директория вместо mktemp ...XXXXXX.pdf.
    # На macOS/BSD шаблон с .pdf после XXXXXX может ломаться.
    tmp_base="${TMPDIR:-/tmp}"
    tmp_base="${tmp_base%/}"
    if [ -z "$tmp_base" ]; then
        tmp_base="/"
    fi

    if ! current_tmp_dir=$(mktemp -d "$tmp_base/pdfcompress.XXXXXX"); then
        echo "  Ошибка: не удалось создать временную директорию."
        problems_found=true
        current_tmp_dir=""
        continue
    fi

    tmp_file="$current_tmp_dir/compressed.pdf"

    # Сжатие через Ghostscript
    if ! "$GS_BIN" \
        -sDEVICE=pdfwrite \
        -dCompatibilityLevel=1.4 \
        -dNOPAUSE \
        -dOptimize=true \
        -dQUIET \
        -dBATCH \
        -dRemoveUnusedFonts=true \
        -dRemoveUnusedImages=true \
        -dOptimizeResources=true \
        -dDetectDuplicateImages \
        -dCompressFonts=true \
        -dEmbedAllFonts=true \
        -dSubsetFonts=true \
        -dPreserveAnnots=true \
        -dPreserveMarkedContent=true \
        -dPreserveOverprintSettings=true \
        -dPreserveHalftoneInfo=true \
        -dPreserveOPIComments=true \
        -dPreserveDeviceN=true \
        -dMaxInlineImageSize=0 \
        -sOutputFile="$tmp_file" \
        -dAutoFilterColorImages=false \
        -dColorImageFilter="$COLOR_FILTER" \
        -dAutoFilterGrayImages=false \
        -dGrayImageFilter="$COLOR_FILTER" \
        -dDownsampleColorImages=false \
        -dDownsampleGrayImages=false \
        -dDownsampleMonoImages=false \
        "$pdf_file"
    then
        echo "  Ошибка: Ghostscript не смог сжать файл."
        problems_found=true
        cleanup_current_tmp_dir
        current_tmp_dir=""
        continue
    fi

    if [ ! -f "$tmp_file" ] || [ ! -s "$tmp_file" ]; then
        echo "  Ошибка: сжатый файл не был создан или получился пустым."
        problems_found=true
        cleanup_current_tmp_dir
        current_tmp_dir=""
        continue
    fi

    if ! compressed_size=$(get_file_size "$tmp_file"); then
        echo "  Ошибка: не удалось определить размер сжатого файла."
        problems_found=true
        cleanup_current_tmp_dir
        current_tmp_dir=""
        continue
    fi

    compressed_percent=$((compressed_size * 100 / original_size))

    # Если сжатый файл меньше 90% от оригинала,
    # значит потенциальная экономия больше 10%.
    if [ $((compressed_size * 100)) -lt $((original_size * MIN_OUTPUT_PERCENT)) ]; then
        if $CHECK_MODE; then
            echo "  ❌ ТРЕБУЕТСЯ СЖАТИЕ: сжатый файл будет составлять ${compressed_percent}% от исходного по размеру!"
            problems_found=true
        else
            backup_file=$(make_backup_path "$pdf_file")

            if cp -p "$pdf_file" "$backup_file" && mv "$tmp_file" "$pdf_file"; then
                echo "  ✅ Сжато: ${original_size} → ${compressed_size} байт, сжатый файл = ${compressed_percent}% от исходного."
                echo "     Backup сохранён: $backup_file"
            else
                echo "  Ошибка: не удалось заменить файл сжатой версией."
                echo "  Backup, если успел создаться: $backup_file"
                problems_found=true
            fi
        fi
    else
        if $CHECK_MODE; then
            echo "  ✅ OK: потенциальное сжатие ≤${THRESHOLD_PERCENT}% — файл уже оптимизирован"
        else
            echo "  Пропуск: потенциальное сжатие ≤${THRESHOLD_PERCENT}% — файл уже оптимизирован"
        fi
    fi

    cleanup_current_tmp_dir
    current_tmp_dir=""

done < <(find "$SOURCE_DIR" -type f -iname "*.pdf" -print0)

# -----------------------------
# Завершение
# -----------------------------
if ! $found_any; then
    echo "PDF-файлы не найдены."
    exit 0
fi

if $CHECK_MODE; then
    if $problems_found; then
        echo "❌ Проверка не пройдена: есть PDF-файлы, которые можно уменьшить больше чем на ${THRESHOLD_PERCENT}%, или были ошибки обработки."
        exit 1
    else
        echo "✅ Все PDF-файлы уже оптимизированы: потенциальное сжатие ≤${THRESHOLD_PERCENT}%."
        exit 0
    fi
else
    if $problems_found; then
        echo "❌ Обработка завершена с ошибками."
        exit 1
    else
        echo "✅ Обработка завершена. Тяжёлые PDF сжаты, оригиналы сохранены с расширением .backup."
        exit 0
    fi
fi