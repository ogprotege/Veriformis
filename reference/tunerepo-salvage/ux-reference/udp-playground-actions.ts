'use server';

import { runUDPProcessor, type UDPInput, type UDPOutput } from '@/ai/flows/udp-processor-flow';
import { z } from 'zod';

// Define validation schema
const UDPFormSchema = z.object({
  content: z.string().min(1, "Content is required").max(1000000, "Content too large (max 1MB)"),
  contentType: z.enum(['text', 'markdown', 'html', 'pdf', 'docx']),
  removeHeaders: z.boolean(),
  removePageNumbers: z.boolean(),
  removeExtraWhitespace: z.boolean(),
  removeSpecialChars: z.boolean(),
  convertToLowercase: z.boolean(),
  removeUrls: z.boolean(),
  removeEmails: z.boolean(),
  chunkingMethod: z.enum(['fixed', 'semantic', 'paragraph', 'sentence', 'sliding']),
  chunkSize: z.number().min(100).max(10000),
  overlap: z.number().min(0).max(500),
  preserveContext: z.boolean(),
  outputFormat: z.enum(['jsonl', 'csv', 'text', 'markdown']),
  addMetadata: z.boolean(),
  generateSummaries: z.boolean(),
  extractKeywords: z.boolean(),
  detectLanguage: z.boolean(),
});

export interface UDPResult {
  success: boolean;
  data?: UDPOutput;
  error?: string;
  fieldErrors?: z.ZodFormattedError<z.infer<typeof UDPFormSchema>>;
}

export async function processDocument(prevState: UDPResult, formData: FormData): Promise<UDPResult> {
  try {
    // Extract form data
    const rawData = {
      content: formData.get('content'),
      contentType: formData.get('contentType') || 'text',
      removeHeaders: formData.get('removeHeaders') === 'on',
      removePageNumbers: formData.get('removePageNumbers') === 'on',
      removeExtraWhitespace: formData.get('removeExtraWhitespace') === 'on',
      removeSpecialChars: formData.get('removeSpecialChars') === 'on',
      convertToLowercase: formData.get('convertToLowercase') === 'on',
      removeUrls: formData.get('removeUrls') === 'on',
      removeEmails: formData.get('removeEmails') === 'on',
      chunkingMethod: formData.get('chunkingMethod') || 'paragraph',
      chunkSize: Number(formData.get('chunkSize')) || 1000,
      overlap: Number(formData.get('overlap')) || 100,
      preserveContext: formData.get('preserveContext') === 'on',
      outputFormat: formData.get('outputFormat') || 'jsonl',
      addMetadata: formData.get('addMetadata') === 'on',
      generateSummaries: formData.get('generateSummaries') === 'on',
      extractKeywords: formData.get('extractKeywords') === 'on',
      detectLanguage: formData.get('detectLanguage') === 'on',
    };

    // Validate input
    const validatedFields = UDPFormSchema.safeParse(rawData);
    
    if (!validatedFields.success) {
      return {
        success: false,
        error: "Invalid input. Please check the fields below.",
        fieldErrors: validatedFields.error.format(),
      };
    }

    // Prepare input for UDP processor
    const udpInput: UDPInput = {
      content: validatedFields.data.content,
      contentType: validatedFields.data.contentType,
      cleaningOptions: {
        removeHeaders: validatedFields.data.removeHeaders,
        removePageNumbers: validatedFields.data.removePageNumbers,
        removeExtraWhitespace: validatedFields.data.removeExtraWhitespace,
        removeSpecialChars: validatedFields.data.removeSpecialChars,
        convertToLowercase: validatedFields.data.convertToLowercase,
        removeUrls: validatedFields.data.removeUrls,
        removeEmails: validatedFields.data.removeEmails,
      },
      chunkingStrategy: {
        method: validatedFields.data.chunkingMethod,
        chunkSize: validatedFields.data.chunkSize,
        overlap: validatedFields.data.overlap,
        preserveContext: validatedFields.data.preserveContext,
      },
      outputFormat: validatedFields.data.outputFormat,
      enhancementOptions: {
        addMetadata: validatedFields.data.addMetadata,
        generateSummaries: validatedFields.data.generateSummaries,
        extractKeywords: validatedFields.data.extractKeywords,
        detectLanguage: validatedFields.data.detectLanguage,
      },
    };

    // Process document
    const result = await runUDPProcessor(udpInput);
    
    return { 
      success: true, 
      data: result 
    };
    
  } catch (e) {
    console.error("Error in processDocument:", e);
    const errorMessage = e instanceof Error ? e.message : "An unexpected error occurred while processing the document.";
    return { 
      success: false, 
      error: errorMessage 
    };
  }
}