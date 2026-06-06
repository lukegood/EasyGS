"""File system tools: read, write, edit, and preview."""

from __future__ import annotations

import codecs
import csv
import gzip
from pathlib import Path
from typing import Any

from easygs.agent.tools.base import Tool


def _resolve_path(path: str, allowed_dir: Path | None = None) -> Path:
    """Resolve path and optionally enforce directory restriction."""
    resolved = Path(path).expanduser().resolve()
    if allowed_dir and not str(resolved).startswith(str(allowed_dir.resolve())):
        raise PermissionError(f"Path {path} is outside allowed directory {allowed_dir}")
    return resolved


FULL_READ_SUFFIXES = {
    ".py",
    ".r",
    ".sh",
    ".bash",
    ".zsh",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".rs",
    ".go",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".md",
    ".sql",
    ".html",
    ".css",
    ".scss",
    ".xml",
}

FULL_READ_FILENAMES = {
    "dockerfile",
    "makefile",
    "justfile",
    "jenkinsfile",
}

TABULAR_SUFFIXES = {".csv", ".tsv", ".tab"}
AUTO_FULL_MAX_BYTES_TEXT = 256 * 1024
AUTO_FULL_MAX_BYTES_TABULAR = 128 * 1024
AUTO_FULL_MAX_ROWS_TABULAR = 200
AUTO_FULL_MAX_COLS_TABULAR = 40
DEFAULT_PREVIEW_MAX_LINES = 200
DEFAULT_PREVIEW_MAX_CHARS = 24000
DEFAULT_TABULAR_MAX_ROWS = 10
DEFAULT_TABULAR_MAX_COLUMNS = 30
DEFAULT_TABULAR_MAX_CELL_CHARS = 120
DEFAULT_VCF_MAX_LINES = 30
DEFAULT_VCF_MAX_COLUMNS = 30
_ENCODING_CANDIDATES = ("utf-8", "utf-8-sig", "utf-16", "utf-16le", "utf-16be", "gb18030")


def _should_full_read(path: Path) -> bool:
    """Return whether a file should always be read fully in auto mode."""
    if path.suffix.lower() in FULL_READ_SUFFIXES:
        return True
    return path.name.lower() in FULL_READ_FILENAMES


def _detect_encoding(path: Path, requested: str | None = None) -> str:
    """Detect file encoding or honor an explicit request."""
    candidate = (requested or "").strip()
    if candidate and candidate.lower() != "auto":
        return candidate

    with path.open("rb") as handle:
        sample = handle.read(4096)

    bom_candidates = (
        (codecs.BOM_UTF8, "utf-8-sig"),
        (codecs.BOM_UTF16_LE, "utf-16le"),
        (codecs.BOM_UTF16_BE, "utf-16be"),
    )
    for bom, encoding in bom_candidates:
        if sample.startswith(bom):
            return encoding

    for encoding in _ENCODING_CANDIDATES:
        try:
            with path.open("r", encoding=encoding) as handle:
                handle.read(2048)
            return encoding
        except UnicodeDecodeError:
            continue

    return "utf-8"


def _format_size(size_bytes: int) -> str:
    """Format file size for human-readable previews."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _preview_text_content(content: str, max_lines: int, max_chars: int) -> tuple[str, bool, int]:
    """Build a preview string constrained by line and character limits."""
    lines: list[str] = []
    total_chars = 0
    shown_lines = 0

    for line in content.splitlines():
        if shown_lines >= max_lines:
            return "\n".join(lines), True, shown_lines
        if total_chars >= max_chars:
            return "\n".join(lines), True, shown_lines

        remaining = max_chars - total_chars
        if len(line) > remaining:
            lines.append(line[:remaining])
            shown_lines += 1
            return "\n".join(lines), True, shown_lines

        lines.append(line)
        total_chars += len(line) + 1
        shown_lines += 1

    if not content:
        return "", False, 0
    return "\n".join(lines), False, shown_lines


def _detect_delimiter(path: Path, encoding: str, requested: str | None = None) -> str:
    """Detect a likely delimiter for a structured text file."""
    candidate = (requested or "").strip()
    if candidate and candidate.lower() != "auto":
        return candidate

    suffix = path.suffix.lower()
    if suffix == ".csv":
        return ","
    if suffix in {".tsv", ".tab"}:
        return "\t"

    with path.open("r", encoding=encoding, errors="replace") as handle:
        sample_lines = [line for line in handle.read(4096).splitlines() if line.strip()][:10]

    if not sample_lines:
        return "\t"

    best_delimiter = "\t"
    best_score = -1
    for delimiter in ("\t", ",", ";", "|"):
        counts = [line.count(delimiter) for line in sample_lines]
        if not counts or max(counts) == 0:
            continue
        nonzero = sum(1 for count in counts if count > 0)
        score = nonzero * 100 - (max(counts) - min(counts))
        if score > best_score:
            best_score = score
            best_delimiter = delimiter
    return best_delimiter


def _is_probably_tabular(path: Path, encoding: str) -> bool:
    """Heuristic for whether a file should be treated as a delimited table."""
    if path.suffix.lower() in TABULAR_SUFFIXES:
        return True

    if path.suffix.lower() not in {".txt", ".dat"}:
        return False

    delimiter = _detect_delimiter(path, encoding)
    with path.open("r", encoding=encoding, errors="replace") as handle:
        sample_lines = [line for line in handle.read(4096).splitlines() if line.strip()][:10]

    if len(sample_lines) < 2:
        return False

    counts = [len(line.split(delimiter)) for line in sample_lines]
    if max(counts) < 3:
        return False
    return max(counts) - min(counts) <= 1


def _format_preview_header(path: Path, encoding: str, size_bytes: int, reason: str, mode: str) -> list[str]:
    """Common header for truncated previews."""
    return [
        f"Preview of {path}",
        f"- Mode: {mode}",
        f"- Encoding: {encoding}",
        f"- Size: {_format_size(size_bytes)} ({size_bytes} bytes)",
        f"- Reason: {reason}",
    ]


def _preview_text_file(path: Path, encoding: str, max_lines: int, max_chars: int, reason: str) -> str:
    """Return a bounded preview for a generic text file."""
    content = path.read_text(encoding=encoding, errors="replace")
    preview, truncated, shown_lines = _preview_text_content(content, max_lines=max_lines, max_chars=max_chars)

    header = _format_preview_header(path, encoding, path.stat().st_size, reason, "preview")
    header.append(f"- Preview lines shown: {shown_lines}")
    header.append(f"- Truncated: {'yes' if truncated else 'no'}")
    header.append("")
    header.append(preview)
    return "\n".join(header).rstrip()


def _preview_text_file_head_tail(
    path: Path,
    encoding: str,
    max_lines: int,
    max_chars: int,
    reason: str,
) -> str:
    """Return a bounded preview showing both the beginning and end of a text file."""
    content = path.read_text(encoding=encoding, errors="replace")
    lines = content.splitlines()
    if not lines:
        return _preview_text_file(path, encoding, max_lines=max_lines, max_chars=max_chars, reason=reason)

    head_lines = max(1, int(max_lines * 0.65))
    tail_lines = max(1, max_lines - head_lines)

    if len(lines) <= max_lines:
        preview, truncated, shown_lines = _preview_text_content(
            content,
            max_lines=max_lines,
            max_chars=max_chars,
        )
        header = _format_preview_header(path, encoding, path.stat().st_size, reason, "preview")
        header.append(f"- Preview lines shown: {shown_lines}")
        header.append(f"- Truncated: {'yes' if truncated else 'no'}")
        header.append("")
        header.append(preview)
        return "\n".join(header).rstrip()

    head = lines[:head_lines]
    tail = lines[-tail_lines:]
    composed = head + ["... omitted ..."] + tail

    while composed and len("\n".join(composed)) > max_chars:
        if len(tail) > 1:
            tail.pop(0)
        elif len(head) > 1:
            head.pop()
        else:
            break
        composed = head + ["... omitted ..."] + tail

    shown_lines = len(head) + len(tail)
    header = _format_preview_header(path, encoding, path.stat().st_size, reason, "preview")
    header.append(f"- Preview lines shown: {shown_lines}")
    header.append("- Truncated: yes")
    header.append("")
    header.extend(composed)
    return "\n".join(header).rstrip()


def _preview_tabular_text(
    path: Path,
    encoding: str,
    delimiter: str,
    max_rows: int,
    max_columns: int,
    max_cell_chars: int,
) -> str:
    """Return a compact preview for a tabular text file."""
    with path.open("r", encoding=encoding, errors="replace", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        rows = list(reader)

    if not rows:
        return (
            f"Tabular preview of {path}\n"
            f"- Encoding: {encoding}\n"
            f"- Delimiter: {repr(delimiter)}\n"
            "- No rows found."
        )

    header = list(rows[0])
    if header:
        header[0] = header[0].lstrip("\ufeff")
    preview_rows = rows[1 : 1 + max_rows]
    column_count = len(header)
    shown_columns = min(column_count, max_columns)
    shown_header = header[:shown_columns]
    remaining_columns = max(column_count - shown_columns, 0)
    remaining_rows = max(len(rows) - 1 - len(preview_rows), 0)

    delimiter_label = {
        "\t": "tab",
        ",": "comma",
        ";": "semicolon",
        "|": "pipe",
    }.get(delimiter, delimiter)

    lines = [
        f"Tabular preview of {path}",
        f"- Encoding: {encoding}",
        f"- Delimiter: {delimiter_label}",
        f"- Size: {_format_size(path.stat().st_size)} ({path.stat().st_size} bytes)",
        f"- Columns ({column_count}): {', '.join(shown_header)}",
    ]
    if remaining_columns:
        lines.append(f"- Additional columns not shown: {remaining_columns}")
    lines.append(f"- Preview rows shown: {len(preview_rows)}")
    if remaining_rows:
        lines.append(f"- Additional rows not shown: {remaining_rows}")
    lines.append("")

    if not preview_rows:
        lines.append("(No data rows found.)")
        return "\n".join(lines)

    for index, row in enumerate(preview_rows, start=1):
        shown_cells = []
        for cell in row[:shown_columns]:
            normalized = cell.replace("\n", "\\n")
            if len(normalized) > max_cell_chars:
                normalized = normalized[:max_cell_chars] + "..."
            shown_cells.append(normalized)
        lines.append(f"row {index}: " + " | ".join(shown_cells))

    return "\n".join(lines)


def _tabular_shape(path: Path, encoding: str, delimiter: str) -> tuple[int, int]:
    """Return total non-empty row count and maximum column count for a delimited file."""
    row_count = 0
    max_columns = 0
    with path.open("r", encoding=encoding, errors="replace", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue
            row_count += 1
            max_columns = max(max_columns, len(row))
    return row_count, max_columns


def _open_vcf_text(path: Path):
    """Open a VCF or VCF.GZ file as text."""
    if path.name.lower().endswith(".vcf.gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="")
    return path.open("r", encoding="utf-8", errors="replace", newline="")


def _is_vcf_path(path: Path) -> bool:
    """Return whether the path points to a VCF-like file."""
    name = path.name.lower()
    return name.endswith(".vcf") or name.endswith(".vcf.gz")


def _preview_vcf_text(
    path: Path,
    max_lines: int,
    max_columns: int,
) -> str:
    """Return a bounded preview for a VCF or VCF.GZ file."""
    preview_lines: list[str] = []
    total_lines = 0
    truncated_columns = False

    with _open_vcf_text(path) as handle:
        for raw_line in handle:
            if total_lines >= max_lines:
                break
            total_lines += 1
            line = raw_line.rstrip("\n\r")
            if "\t" not in line:
                preview_lines.append(line)
                continue

            columns = line.split("\t")
            shown_columns = columns[:max_columns]
            if len(columns) > max_columns:
                truncated_columns = True
                shown_columns.append(f"... ({len(columns) - max_columns} more columns)")
            preview_lines.append("\t".join(shown_columns))

    with _open_vcf_text(path) as handle:
        actual_total_lines = sum(1 for _ in handle)

    remaining_lines = max(actual_total_lines - len(preview_lines), 0)
    lines = [
        f"VCF preview of {path}",
        f"- Compression: {'gzip' if path.name.lower().endswith('.vcf.gz') else 'plain text'}",
        f"- Size: {_format_size(path.stat().st_size)} ({path.stat().st_size} bytes)",
        f"- Preview lines shown: {len(preview_lines)}",
        f"- Max columns shown per line: {max_columns}",
        f"- Additional lines not shown: {remaining_lines}",
        f"- Columns truncated on some lines: {'yes' if truncated_columns else 'no'}",
        "",
    ]
    lines.extend(preview_lines or ["(No lines found.)"])
    return "\n".join(lines)


class ReadFileTool(Tool):  # 读取文件内容
    """Tool to read file contents."""
    
    def __init__(self, allowed_dir: Path | None = None):
        self._allowed_dir = allowed_dir  # 允许的目录

    @property  # 把方法包装成属性来访问，不用带括号了
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return (
            "Read a file. Code, script, markdown, and config-like files are returned in full. "
            "Moderately sized non-code text files may also be returned in full. For larger files, "
            "auto mode returns a bounded preview instead of the full content."
        )
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to read"
                },
                "mode": {
                    "type": "string",
                    "description": "Read mode: auto, full, or preview. Defaults to auto.",
                    "enum": ["auto", "full", "preview"],
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum lines to return in preview mode.",
                    "minimum": 1,
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum characters to return in preview mode.",
                    "minimum": 1,
                },
                "encoding": {
                    "type": "string",
                    "description": "Text encoding to use. Defaults to auto-detection.",
                },
            },
            "required": ["path"]
        }
    
    async def execute(
        self,
        path: str,
        mode: str = "auto",
        max_lines: int = DEFAULT_PREVIEW_MAX_LINES,
        max_chars: int = DEFAULT_PREVIEW_MAX_CHARS,
        encoding: str = "auto",
        **kwargs: Any,
    ) -> str:
        try:
            file_path = _resolve_path(path, self._allowed_dir)
            if not file_path.exists():
                return f"Error: File not found: {path}"
            if not file_path.is_file():
                return f"Error: Not a file: {path}"

            resolved_encoding = _detect_encoding(file_path, encoding)
            selected_mode = (mode or "auto").strip().lower() or "auto"
            size_bytes = file_path.stat().st_size

            if selected_mode == "full" or _should_full_read(file_path):
                return file_path.read_text(encoding=resolved_encoding, errors="replace")

            if selected_mode == "preview":
                return _preview_text_file(
                    file_path,
                    encoding=resolved_encoding,
                    max_lines=max_lines,
                    max_chars=max_chars,
                    reason="preview mode requested",
                )

            is_tabular = _is_probably_tabular(file_path, resolved_encoding)

            if is_tabular:
                if size_bytes <= AUTO_FULL_MAX_BYTES_TABULAR:
                    delimiter = _detect_delimiter(file_path, resolved_encoding)
                    row_count, column_count = _tabular_shape(file_path, resolved_encoding, delimiter)
                    if (
                        row_count <= AUTO_FULL_MAX_ROWS_TABULAR
                        and column_count <= AUTO_FULL_MAX_COLS_TABULAR
                    ):
                        return file_path.read_text(encoding=resolved_encoding, errors="replace")

                    return _preview_tabular_text(
                        file_path,
                        encoding=resolved_encoding,
                        delimiter=delimiter,
                        max_rows=DEFAULT_TABULAR_MAX_ROWS,
                        max_columns=DEFAULT_TABULAR_MAX_COLUMNS,
                        max_cell_chars=DEFAULT_TABULAR_MAX_CELL_CHARS,
                    )

                delimiter = _detect_delimiter(file_path, resolved_encoding)
                return _preview_tabular_text(
                    file_path,
                    encoding=resolved_encoding,
                    delimiter=delimiter,
                    max_rows=DEFAULT_TABULAR_MAX_ROWS,
                    max_columns=DEFAULT_TABULAR_MAX_COLUMNS,
                    max_cell_chars=DEFAULT_TABULAR_MAX_CELL_CHARS,
                )

            if size_bytes <= AUTO_FULL_MAX_BYTES_TEXT:
                return file_path.read_text(encoding=resolved_encoding, errors="replace")

            reason = (
                "non-whitelisted text file exceeded auto full-read threshold "
                f"({AUTO_FULL_MAX_BYTES_TEXT} bytes)"
            )
            return _preview_text_file_head_tail(
                file_path,
                encoding=resolved_encoding,
                max_lines=max_lines,
                max_chars=max_chars,
                reason=reason,
            )
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error reading file: {str(e)}"


class PreviewTabularFileTool(Tool):
    """Tool to preview structured tabular text files."""

    def __init__(self, allowed_dir: Path | None = None):
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "preview_tabular_file"

    @property
    def description(self) -> str:
        return (
            "Preview a structured tabular file such as CSV, TSV, or tabular TXT. "
            "Returns detected encoding, delimiter, column names, and a few sample rows."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The tabular file path to preview",
                },
                "encoding": {
                    "type": "string",
                    "description": "Text encoding to use. Defaults to auto-detection.",
                },
                "delimiter": {
                    "type": "string",
                    "description": "Delimiter to use. Defaults to auto-detection.",
                },
                "max_rows": {
                    "type": "integer",
                    "description": "Maximum number of data rows to preview.",
                    "minimum": 1,
                },
                "max_columns": {
                    "type": "integer",
                    "description": "Maximum number of columns to preview.",
                    "minimum": 1,
                },
                "max_cell_chars": {
                    "type": "integer",
                    "description": "Maximum number of characters to show per cell.",
                    "minimum": 1,
                },
            },
            "required": ["path"],
        }

    async def execute(
        self,
        path: str,
        encoding: str = "auto",
        delimiter: str = "auto",
        max_rows: int = DEFAULT_TABULAR_MAX_ROWS,
        max_columns: int = DEFAULT_TABULAR_MAX_COLUMNS,
        max_cell_chars: int = DEFAULT_TABULAR_MAX_CELL_CHARS,
        **kwargs: Any,
    ) -> str:
        try:
            file_path = _resolve_path(path, self._allowed_dir)
            if not file_path.exists():
                return f"Error: File not found: {path}"
            if not file_path.is_file():
                return f"Error: Not a file: {path}"

            resolved_encoding = _detect_encoding(file_path, encoding)
            if not _is_probably_tabular(file_path, resolved_encoding):
                return (
                    f"Error: Could not confidently detect a tabular structure in {file_path}. "
                    "Use read_file for regular text files."
                )

            resolved_delimiter = _detect_delimiter(file_path, resolved_encoding, delimiter)
            return _preview_tabular_text(
                file_path,
                encoding=resolved_encoding,
                delimiter=resolved_delimiter,
                max_rows=max_rows,
                max_columns=max_columns,
                max_cell_chars=max_cell_chars,
            )
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error previewing tabular file: {str(e)}"


class PreviewVcfFileTool(Tool):
    """Tool to preview VCF and VCF.GZ files safely."""

    def __init__(self, allowed_dir: Path | None = None):
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "preview_vcf_file"

    @property
    def description(self) -> str:
        return (
            "Preview a VCF or VCF.GZ file safely by returning only the first few lines "
            "and the first few columns of tab-delimited records."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The VCF or VCF.GZ file path to preview",
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum number of lines to preview. Defaults to 30.",
                    "minimum": 1,
                },
                "max_columns": {
                    "type": "integer",
                    "description": "Maximum number of columns to show per tab-delimited line. Defaults to 30.",
                    "minimum": 1,
                },
            },
            "required": ["path"],
        }

    async def execute(
        self,
        path: str,
        max_lines: int = DEFAULT_VCF_MAX_LINES,
        max_columns: int = DEFAULT_VCF_MAX_COLUMNS,
        **kwargs: Any,
    ) -> str:
        try:
            file_path = _resolve_path(path, self._allowed_dir)
            if not file_path.exists():
                return f"Error: File not found: {path}"
            if not file_path.is_file():
                return f"Error: Not a file: {path}"
            if not _is_vcf_path(file_path):
                return f"Error: File must end with .vcf or .vcf.gz: {file_path}"

            return _preview_vcf_text(file_path, max_lines=max_lines, max_columns=max_columns)
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error previewing VCF file: {str(e)}"


class WriteFileTool(Tool):  # 写入文件
    """Tool to write content to a file."""
    
    def __init__(self, allowed_dir: Path | None = None):
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "write_file"
    
    @property
    def description(self) -> str:
        return "Write content to a file at the given path. Creates parent directories if needed."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to write to"
                },
                "content": {
                    "type": "string",
                    "description": "The content to write"
                }
            },
            "required": ["path", "content"]
        }
    
    async def execute(self, path: str, content: str, **kwargs: Any) -> str:
        try:
            file_path = _resolve_path(path, self._allowed_dir)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return f"Successfully wrote {len(content)} bytes to {path}"
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error writing file: {str(e)}"


class EditFileTool(Tool):  # 编辑文件工具，通过搜索替换来实现
    """Tool to edit a file by replacing text."""
    
    def __init__(self, allowed_dir: Path | None = None):
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "edit_file"
    
    @property
    def description(self) -> str:
        return "Edit a file by replacing old_text with new_text. The old_text must exist exactly in the file."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to edit"
                },
                "old_text": {
                    "type": "string",
                    "description": "The exact text to find and replace"
                },
                "new_text": {
                    "type": "string",
                    "description": "The text to replace with"
                }
            },
            "required": ["path", "old_text", "new_text"]
        }
    
    async def execute(self, path: str, old_text: str, new_text: str, **kwargs: Any) -> str:
        try:
            file_path = _resolve_path(path, self._allowed_dir)
            if not file_path.exists():
                return f"Error: File not found: {path}"
            
            content = file_path.read_text(encoding="utf-8")
            
            if old_text not in content:
                return f"Error: old_text not found in file. Make sure it matches exactly."
            
            # Count occurrences
            count = content.count(old_text)
            if count > 1:
                return f"Warning: old_text appears {count} times. Please provide more context to make it unique."
            
            new_content = content.replace(old_text, new_text, 1)
            file_path.write_text(new_content, encoding="utf-8")
            
            return f"Successfully edited {path}"
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error editing file: {str(e)}"


class ListDirTool(Tool):  # 列出目录内容工具
    """Tool to list directory contents."""
    
    def __init__(self, allowed_dir: Path | None = None):
        self._allowed_dir = allowed_dir

    @property
    def name(self) -> str:
        return "list_dir"
    
    @property
    def description(self) -> str:
        return "List the contents of a directory."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The directory path to list"
                }
            },
            "required": ["path"]
        }
    
    async def execute(self, path: str, **kwargs: Any) -> str:
        try:
            dir_path = _resolve_path(path, self._allowed_dir)
            if not dir_path.exists():
                return f"Error: Directory not found: {path}"
            if not dir_path.is_dir():
                return f"Error: Not a directory: {path}"
            
            items = []
            for item in sorted(dir_path.iterdir()):
                prefix = "📁 " if item.is_dir() else "📄 "
                items.append(f"{prefix}{item.name}")
            
            if not items:
                return f"Directory {path} is empty"
            
            return "\n".join(items)
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error listing directory: {str(e)}"
