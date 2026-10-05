// location: frontend/components/admin/image-upload-classify.tsx
"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { ImagePlus, Loader2, Sparkles, Upload, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

import { useUploadProductImage } from "@/hooks/use-admin-products";
import { cn } from "@/lib/utils";
import type { AutoCategorizeResponse } from "@/lib/api-types";

const MAX_FILE_MB = 5;
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

export function ImageUploadClassify() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [sku, setSku] = useState("");
  const [description, setDescription] = useState("");

  const [result, setResult] = useState<AutoCategorizeResponse | null>(null);

  const upload = useUploadProductImage();

  // ──────────────────────────────────────────────────────────
  // File handling
  // ──────────────────────────────────────────────────────────
  function handleFile(f: File) {
    if (!ACCEPTED_TYPES.includes(f.type)) {
      alert("Please upload a JPEG, PNG, or WebP image.");
      return;
    }
    if (f.size > MAX_FILE_MB * 1024 * 1024) {
      alert(`File too large. Max ${MAX_FILE_MB} MB.`);
      return;
    }
    setFile(f);
    const url = URL.createObjectURL(f);
    setPreview(url);
    setResult(null);
  }

  function clearFile() {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview(null);
    setResult(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }

  // ──────────────────────────────────────────────────────────
  // Submit
  // ──────────────────────────────────────────────────────────
  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;

    upload.mutate(
      {
        image: file,
        name: name.trim(),
        price: price.trim(),
        sku: sku.trim() || undefined,
        description: description.trim() || undefined,
      },
      {
        onSuccess: (res) => {
          setResult(res);
          if (res.status === "created") {
            // Success → redirect to edit page after brief delay
            setTimeout(() => {
              router.push(`/dashboard/products/${res.product_id}/edit`);
            }, 1500);
          }
        },
      },
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            ML-powered auto-categorization
          </CardTitle>
          <CardDescription>
            Upload a product image. Our classifier will predict the category
            and create the product automatically.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-6">
            {/* Drop zone */}
            <div className="space-y-2">
              <Label>Product image</Label>
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                onClick={() => fileInputRef.current?.click()}
                className={cn(
                  "relative flex min-h-[200px] cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-6 text-center transition-colors",
                  dragging
                    ? "border-primary bg-primary/5"
                    : "border-muted-foreground/25 hover:border-primary/50",
                  preview && "border-solid",
                )}
              >
                {preview ? (
                  <>
                    {/* Preview */}
                    <div className="relative">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={preview}
                        alt="Preview"
                        className="max-h-48 rounded-md object-contain"
                      />
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          clearFile();
                        }}
                        className="absolute -right-2 -top-2 rounded-full bg-destructive p-1 text-destructive-foreground shadow-md hover:bg-destructive/90"
                        aria-label="Remove image"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {file?.name} · {((file?.size ?? 0) / 1024).toFixed(0)} KB
                    </p>
                  </>
                ) : (
                  <>
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
                      <ImagePlus className="h-6 w-6 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">
                        Click to upload or drag & drop
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        JPEG, PNG or WebP · max {MAX_FILE_MB} MB
                      </p>
                    </div>
                  </>
                )}

                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED_TYPES.join(",")}
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleFile(f);
                  }}
                  disabled={upload.isPending}
                />
              </div>
            </div>

            {/* Name + Price */}
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="upload-name">
                  Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="upload-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Blue Cotton Shirt"
                  required
                  disabled={upload.isPending}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="upload-price">
                  Price (USD) <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="upload-price"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder="29.99"
                  inputMode="decimal"
                  pattern="^\d+(\.\d{1,2})?$"
                  required
                  disabled={upload.isPending}
                />
              </div>
            </div>

            {/* SKU */}
            <div className="space-y-2">
              <Label htmlFor="upload-sku">SKU (optional)</Label>
              <Input
                id="upload-sku"
                value={sku}
                onChange={(e) => setSku(e.target.value)}
                placeholder="Auto-generated if empty"
                className="font-mono"
                disabled={upload.isPending}
              />
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="upload-desc">Description (optional)</Label>
              <Textarea
                id="upload-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Product details…"
                rows={3}
                disabled={upload.isPending}
              />
            </div>

            {/* Submit */}
            <Button
              type="submit"
              size="lg"
              className="w-full"
              disabled={!file || !name || !price || upload.isPending}
            >
              {upload.isPending ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Classifying & uploading…
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-5 w-5" />
                  Upload &amp; auto-categorize
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Result panel */}
      {result && (
        <Card
          className={cn(
            result.status === "created"
              ? "border-green-500/50 bg-green-50/50 dark:bg-green-950/20"
              : "border-yellow-500/50 bg-yellow-50/50 dark:bg-yellow-950/20",
          )}
        >
          <CardHeader>
            <CardTitle>
              {result.status === "created"
                ? "✅ Product created"
                : "⚠️ Needs review"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {result.status === "created" ? (
              <>
                <p className="text-sm">
                  <strong>#{result.product_id}</strong> {result.name} —{" "}
                  {result.category_name}
                </p>
                <p className="text-xs text-muted-foreground">
                  Confidence:{" "}
                  {result.confidence
                    ? `${Math.round(result.confidence * 100)}%`
                    : "N/A"}
                </p>
                <p className="text-xs text-muted-foreground">
                  Redirecting to edit page…
                </p>
              </>
            ) : (
              <>
                <p className="text-sm">
                  Classifier predicted <strong>{result.ml_category}</strong>{" "}
                  with only {Math.round(result.confidence * 100)}% confidence
                  (threshold: {Math.round(result.threshold * 100)}%).
                </p>
                <div>
                  <p className="text-xs font-medium uppercase text-muted-foreground">
                    Top suggestions
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {result.suggestions.map((s) => (
                      <Badge key={s.category} variant="secondary">
                        {s.category} · {Math.round(s.confidence * 100)}%
                      </Badge>
                    ))}
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Please use the &ldquo;Manual entry&rdquo; tab and pick a
                  category yourself.
                </p>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
