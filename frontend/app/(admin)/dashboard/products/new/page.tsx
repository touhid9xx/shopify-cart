"use client";

import { useState } from "react";
import { ImagePlus, Keyboard } from "lucide-react";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ProductForm } from "@/components/admin/product-form";
import { ImageUploadClassify } from "@/components/admin/image-upload-classify";

export default function NewProductPage() {
  const [tab, setTab] = useState<"upload" | "manual">("upload");

  return (
    <div className="container mx-auto max-w-3xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">New product</h1>
        <p className="mt-2 text-muted-foreground">
          Upload an image and let the ML classifier assign a category — or
          enter the details manually.
        </p>
      </div>

      <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
        <TabsList className="mb-6 grid w-full grid-cols-2">
          <TabsTrigger value="upload">
            <ImagePlus className="mr-2 h-4 w-4" />
            Upload image
          </TabsTrigger>
          <TabsTrigger value="manual">
            <Keyboard className="mr-2 h-4 w-4" />
            Manual entry
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upload">
          <ImageUploadClassify />
        </TabsContent>

        <TabsContent value="manual">
          <ProductForm />
        </TabsContent>
      </Tabs>
    </div>
  );
}
