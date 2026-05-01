import { useCallback, useRef, useState } from "react";
import { Upload, X, Image as ImageIcon, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import { compressForUpload } from "@/lib/compress";

interface Props {
  label?: string;
  file: File | null;
  onChange: (next: File | null) => void;
  accept?: string;
  className?: string;
  /** Show a "Compressing…" hint while compressForUpload runs. */
  showCompressionHint?: boolean;
}

const ACCEPTED =
  "image/png,image/jpeg,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx";

function isDocx(f: File): boolean {
  return (
    f.type ===
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
    f.name.toLowerCase().endsWith(".docx")
  );
}

export function ImageUploader({
  label = "Upload image",
  file,
  onChange,
  accept = ACCEPTED,
  className,
  showCompressionHint = true,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [compressing, setCompressing] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [originalSize, setOriginalSize] = useState<number | null>(null);
  const [compressedSize, setCompressedSize] = useState<number | null>(null);

  const setFile = useCallback(
    async (raw: File | null) => {
      if (!raw) {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        setPreviewUrl(null);
        setOriginalSize(null);
        setCompressedSize(null);
        onChange(null);
        return;
      }
      setOriginalSize(raw.size);
      // .docx skips compression and image preview — server extracts the
      // embedded diagram.
      if (isDocx(raw)) {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        setPreviewUrl(null);
        setCompressedSize(null);
        onChange(raw);
        return;
      }
      setCompressing(true);
      try {
        const compressed = await compressForUpload(raw);
        setCompressedSize(compressed.size);
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        setPreviewUrl(URL.createObjectURL(compressed));
        onChange(compressed);
      } finally {
        setCompressing(false);
      }
    },
    [onChange, previewUrl],
  );

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files?.[0];
      if (f) setFile(f);
    },
    [setFile],
  );

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <span className="text-sm font-medium text-kpmg-darkBlue">{label}</span>

      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={cn(
          "relative flex min-h-[200px] cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-6 text-center transition-colors",
          dragOver
            ? "border-kpmg-cobalt bg-kpmg-lightBlue/30"
            : "border-gray-300 hover:border-kpmg-blue hover:bg-gray-50",
          file && "border-kpmg-blue bg-white",
        )}
      >
        {file && isDocx(file) ? (
          <>
            <FileText className="h-10 w-10 text-kpmg-blue" />
            <div className="flex items-center gap-3 text-sm text-gray-700">
              <span className="font-medium">{file.name}</span>
              {originalSize !== null && (
                <span className="text-xs text-gray-500">
                  {(originalSize / 1024 / 1024).toFixed(2)} MB
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500">
              Server will extract the first embedded diagram and any prose
              context.
            </p>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
              }}
              className="absolute right-2 top-2 rounded-full bg-white p-1 text-gray-500 shadow-sm hover:text-kpmg-blue focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-kpmg-cobalt"
              aria-label="Remove document"
            >
              <X className="h-4 w-4" />
            </button>
          </>
        ) : previewUrl ? (
          <>
            <img
              src={previewUrl}
              alt="Selected architecture diagram preview"
              className="max-h-56 w-auto rounded-md border border-gray-200 object-contain"
            />
            <div className="flex items-center gap-3 text-xs text-gray-600">
              <ImageIcon className="h-3.5 w-3.5" />
              <span>{file?.name}</span>
              {compressedSize !== null && originalSize !== null && (
                <span>
                  {(originalSize / 1024 / 1024).toFixed(1)} MB →{" "}
                  {(compressedSize / 1024 / 1024).toFixed(1)} MB
                </span>
              )}
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
              }}
              className="absolute right-2 top-2 rounded-full bg-white p-1 text-gray-500 shadow-sm hover:text-kpmg-blue focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-kpmg-cobalt"
              aria-label="Remove image"
            >
              <X className="h-4 w-4" />
            </button>
          </>
        ) : (
          <>
            <Upload className="h-8 w-8 text-kpmg-blue" />
            <div className="text-sm">
              <span className="font-semibold text-kpmg-blue">
                Click to upload
              </span>
              <span className="text-gray-600"> or drag and drop</span>
            </div>
            <p className="text-xs text-gray-500">
              PNG, JPEG, or DOCX — up to 15 MB
            </p>
          </>
        )}

        {compressing && showCompressionHint && (
          <div className="absolute bottom-2 right-2 rounded bg-kpmg-lightBlue/80 px-2 py-0.5 text-xs text-kpmg-darkBlue">
            Compressing…
          </div>
        )}

        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="sr-only"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          aria-label={label}
        />
      </div>
    </div>
  );
}
