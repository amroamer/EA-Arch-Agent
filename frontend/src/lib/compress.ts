/**
 * Client-side image compression before multipart upload.
 *
 * Architecture screenshots are often huge (4K+ resolution). We resize the
 * longest edge to 1568 px (Gemma vision's preferred tile ceiling) and
 * re-encode at JPEG q85. Server-side image_utils does the same as a
 * defense-in-depth measure, but doing it client-side avoids the bandwidth
 * cost of uploading 20 MB only to be rejected.
 */
import imageCompression from "browser-image-compression";

const TARGET_LONGEST_EDGE = 1568;
const TARGET_MAX_BYTES = 4 * 1024 * 1024; // 4 MB after compression

export async function compressForUpload(file: File): Promise<File> {
  // Compression only applies to raster images. Word documents (and any
  // other non-image type) pass through unchanged.
  if (!file.type.startsWith("image/")) return file;

  // Skip compression for already-tiny images.
  if (file.size <= 256 * 1024) return file;

  return imageCompression(file, {
    maxSizeMB: TARGET_MAX_BYTES / (1024 * 1024),
    maxWidthOrHeight: TARGET_LONGEST_EDGE,
    useWebWorker: true,
    initialQuality: 0.85,
    fileType: file.type === "image/png" ? "image/png" : "image/jpeg",
  });
}
