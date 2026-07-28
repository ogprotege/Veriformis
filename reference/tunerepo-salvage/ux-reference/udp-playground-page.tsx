'use client';

import { useState } from 'react';
import { useFormState, useFormStatus } from 'react-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, PlayCircle, UploadCloud, Settings2, Download, FileText, Loader2, AlertTriangle, Copy } from 'lucide-react';
import Link from 'next/link';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import {  AlertDescriptionTitle } from '@/components/ui/alert';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { useToast } from '@/hooks/use-toast';
import { processDocument, type UDPResult } from './actions';

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <Button type="submit" disabled={pending} className="w-full" size="lg">
      {pending ? (
        <>
          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          Processing...
        </>
      ) : (
        <>
          <PlayCircle className="mr-2 h-5 w-5" />
          Process Document
        </>
      )}
    </Button>
  );
}

export default function UdpPlaygroundPage() {
  const { toast } = useToast();
  const initialState: UDPResult = { success: false };
  const [state, formAction] = useFormState(processDocument, initialState);
  const [isLoading, setIsLoading] = useState(false);
  
  // Form state
  const [inputText, setInputText] = useState<string>('');
  const [contentType, setContentType] = useState<string>('text');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  
  // Cleaning options
  const [removeHeaders, setRemoveHeaders] = useState(false);
  const [removePageNumbers, setRemovePageNumbers] = useState(true);
  const [removeExtraWhitespace, setRemoveExtraWhitespace] = useState(true);
  const [removeSpecialChars, setRemoveSpecialChars] = useState(false);
  const [convertToLowercase, setConvertToLowercase] = useState(false);
  const [removeUrls, setRemoveUrls] = useState(false);
  const [removeEmails, setRemoveEmails] = useState(false);
  
  // Chunking options
  const [chunkingMethod, setChunkingMethod] = useState<string>('paragraph');
  const [chunkSize, setChunkSize] = useState<number>(1000);
  const [overlap, setOverlap] = useState<number>(100);
  const [preserveContext, setPreserveContext] = useState(true);
  
  // Output options
  const [outputFormat, setOutputFormat] = useState<string>('jsonl');
  const [addMetadata, setAddMetadata] = useState(true);
  const [generateSummaries, setGenerateSummaries] = useState(false);
  const [extractKeywords, setExtractKeywords] = useState(false);
  const [detectLanguage, setDetectLanguage] = useState(true);

  // Sample text
  const sampleText = `Introduction to Machine Learning

Machine learning is a subset of artificial intelligence that provides systems the ability to learn and improve from experience without being explicitly programmed. In recent years, machine learning has become one of the most important technologies of our time.

Types of Machine Learning

There are three main types of machine learning:

1. Supervised Learning: The algorithm learns from labeled training data, and makes predictions based on that data. Common applications include spam detection, image recognition, and weather forecasting.

2. Unsupervised Learning: The algorithm finds patterns in unlabeled data. It&apos;s used for clustering, dimensionality reduction, and anomaly detection.

3. Reinforcement Learning: The algorithm learns by interacting with an environment and receiving rewards or penalties. This is commonly used in robotics, gaming, and navigation.

Applications and Future

Machine learning is transforming industries from healthcare to finance, enabling breakthroughs in drug discovery, fraud detection, and personalized recommendations. As we continue to generate more data and develop more powerful algorithms, the potential applications of machine learning will only continue to grow.`;

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setUploadedFile(file);
      const text = await file.text();
      setInputText(text);
      toast({ title: "File Selected", description: `${file.name} is ready for processing.` });
    }
  };

  const handleDrop = async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    const file = event.dataTransfer.files?.[0];
    if (file) {
      setUploadedFile(file);
      const text = await file.text();
      setInputText(text);
      toast({ title: "File Dropped", description: `${file.name} is ready for processing.` });
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
  };

  const handleCopy = async (text: string) => {
    if (!text) {
      toast({ variant: "destructive", title: "Error", description: "No content to copy." });
      return;
    }
    
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        toast({ title: "Success", description: "Content copied to clipboard!" });
      } else {
        throw new Error("Clipboard API not available");
      }
    } catch (err) {
      toast({ variant: "destructive", title: "Error", description: "Failed to copy content." });
    }
  };

  const handleDownload = (content: string, format: string) => {
    if (!content) {
      toast({ variant: "destructive", title: "Error", description: "No content to download." });
      return;
    }
    
    try {
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `processed_document.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast({ title: "Success", description: "Download started." });
    } catch (err) {
      toast({ variant: "destructive", title: "Error", description: "Failed to download content." });
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <Button variant="outline" asChild className="mb-6">
        <Link href="/tools/udp">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to UDP
        </Link>
      </Button>

      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-4">UDP Interactive Playground</h1>
        <p className="text-muted-foreground text-lg">
          Process documents with advanced cleaning, chunking, and transformation capabilities.
        </p>
      </div>

      <div className="grid md:grid-cols-5 gap-6">
        {/* Left Panel - Input and Configuration */}
        <div className="md:col-span-3 space-y-6">
          <form action={async (formData) => {
            setIsLoading(true);
            try {
              await formAction(formData);
            } finally {
              setIsLoading(false);
            }
          }}>
            {/* Hidden field for content */}
            <input type="hidden" name="content" value={inputText} />
            <input type="hidden" name="contentType" value={contentType} />
            
            {/* Input Section */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <FileText className="mr-2 h-5 w-5" />
                  Document Input
                </CardTitle>
                <CardDescription>Upload a file or paste your text</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div 
                  className="border-2 border-dashed rounded-lg p-8 text-center hover:border-primary transition-colors cursor-pointer"
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onClick={() => document.getElementById('file-upload')?.click()}
                >
                  <input
                    id="file-upload"
                    type="file"
                    className="hidden"
                    accept=".txt,.md,.html,.csv,.json"
                    onChange={handleFileUpload}
                  />
                  <UploadCloud className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-sm text-muted-foreground mb-2">
                    Drag and drop your file here, or click to browse
                  </p>
                  {uploadedFile && (
                    <Badge variant="secondary" className="mt-2">
                      {uploadedFile.name}
                    </Badge>
                  )}
                </div>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-background px-2 text-muted-foreground">Or paste text</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <Textarea
                    placeholder="Paste your document text here..."
                    className="min-h-[200px] font-mono text-sm"
                    value={inputText}
                    onChange={(e) => {
                      setInputText(e.target.value);
                      setUploadedFile(null);
                    }}
                  />
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">
                      {inputText.length} characters
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setInputText(sampleText)}
                    >
                      Load Sample Text
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Cleaning Options */}
            <Card className="mt-6">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Settings2 className="mr-2 h-5 w-5" />
                  Cleaning Options
                </CardTitle>
                <CardDescription>Configure how to clean your document</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center space-x-2">
                    <Checkbox 
                      id="removeHeaders" 
                      name="removeHeaders"
                      checked={removeHeaders}
                      onCheckedChange={(checked) => setRemoveHeaders(checked as boolean)}
                    />
                    <Label htmlFor="removeHeaders">Remove headers/footers</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox 
                      id="removePageNumbers" 
                      name="removePageNumbers"
                      checked={removePageNumbers}
                      onCheckedChange={(checked) => setRemovePageNumbers(checked as boolean)}
                    />
                    <Label htmlFor="removePageNumbers">Remove page numbers</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox 
                      id="removeExtraWhitespace" 
                      name="removeExtraWhitespace"
                      checked={removeExtraWhitespace}
                      onCheckedChange={(checked) => setRemoveExtraWhitespace(checked as boolean)}
                    />
                    <Label htmlFor="removeExtraWhitespace">Normalize whitespace</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox 
                      id="removeSpecialChars" 
                      name="removeSpecialChars"
                      checked={removeSpecialChars}
                      onCheckedChange={(checked) => setRemoveSpecialChars(checked as boolean)}
                    />
                    <Label htmlFor="removeSpecialChars">Remove special chars</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox 
                      id="convertToLowercase" 
                      name="convertToLowercase"
                      checked={convertToLowercase}
                      onCheckedChange={(checked) => setConvertToLowercase(checked as boolean)}
                    />
                    <Label htmlFor="convertToLowercase">Convert to lowercase</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox 
                      id="removeUrls" 
                      name="removeUrls"
                      checked={removeUrls}
                      onCheckedChange={(checked) => setRemoveUrls(checked as boolean)}
                    />
                    <Label htmlFor="removeUrls">Remove URLs</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox 
                      id="removeEmails" 
                      name="removeEmails"
                      checked={removeEmails}
                      onCheckedChange={(checked) => setRemoveEmails(checked as boolean)}
                    />
                    <Label htmlFor="removeEmails">Remove emails</Label>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Chunking Strategy */}
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>Chunking Strategy</CardTitle>
                <CardDescription>How to split your document into chunks</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="chunkingMethod">Chunking Method</Label>
                  <Select name="chunkingMethod" value={chunkingMethod} onValueChange={setChunkingMethod}>
                    <SelectTrigger id="chunkingMethod">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="fixed">Fixed Size</SelectItem>
                      <SelectItem value="semantic">Semantic</SelectItem>
                      <SelectItem value="paragraph">By Paragraph</SelectItem>
                      <SelectItem value="sentence">By Sentence</SelectItem>
                      <SelectItem value="sliding">Sliding Window</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="chunkSize">Chunk Size: {chunkSize} characters</Label>
                  <Slider
                    id="chunkSize"
                    name="chunkSize"
                    min={100}
                    max={5000}
                    step={100}
                    value={[chunkSize]}
                    onValueChange={(value) => setChunkSize(value[0])}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="overlap">Overlap: {overlap} characters</Label>
                  <Slider
                    id="overlap"
                    name="overlap"
                    min={0}
                    max={500}
                    step={10}
                    value={[overlap]}
                    onValueChange={(value) => setOverlap(value[0])}
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="preserveContext" 
                    name="preserveContext"
                    checked={preserveContext}
                    onCheckedChange={(checked) => setPreserveContext(checked as boolean)}
                  />
                  <Label htmlFor="preserveContext">Preserve semantic context</Label>
                </div>
              </CardContent>
            </Card>

            {/* Output Options */}
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>Output Options</CardTitle>
                <CardDescription>Configure the output format and enhancements</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="outputFormat">Output Format</Label>
                  <Select name="outputFormat" value={outputFormat} onValueChange={setOutputFormat}>
                    <SelectTrigger id="outputFormat">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="jsonl">JSONL (JSON Lines)</SelectItem>
                      <SelectItem value="csv">CSV</SelectItem>
                      <SelectItem value="text">Plain Text</SelectItem>
                      <SelectItem value="markdown">Markdown</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Enhancements</Label>
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <Checkbox 
                        id="addMetadata" 
                        name="addMetadata"
                        checked={addMetadata}
                        onCheckedChange={(checked) => setAddMetadata(checked as boolean)}
                      />
                      <Label htmlFor="addMetadata">Add metadata to chunks</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox 
                        id="generateSummaries" 
                        name="generateSummaries"
                        checked={generateSummaries}
                        onCheckedChange={(checked) => setGenerateSummaries(checked as boolean)}
                      />
                      <Label htmlFor="generateSummaries">Generate chunk summaries</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox 
                        id="extractKeywords" 
                        name="extractKeywords"
                        checked={extractKeywords}
                        onCheckedChange={(checked) => setExtractKeywords(checked as boolean)}
                      />
                      <Label htmlFor="extractKeywords">Extract keywords</Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox 
                        id="detectLanguage" 
                        name="detectLanguage"
                        checked={detectLanguage}
                        onCheckedChange={(checked) => setDetectLanguage(checked as boolean)}
                      />
                      <Label htmlFor="detectLanguage">Detect language</Label>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="mt-6">
              <SubmitButton />
            </div>
          </form>
        </div>

        {/* Right Panel - Results */}
        <div className="md:col-span-2">
          <Card className="sticky top-6">
            <CardHeader>
              <CardTitle>Processing Results</CardTitle>
              <CardDescription>View processed output and statistics</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {isLoading && (
                <div className="flex flex-col items-center justify-center py-10">
                  <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
                  <p className="text-muted-foreground">Processing document...</p>
                </div>
              )}

              {state.error && !state.fieldErrors && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>Processing Failed</AlertTitle>
                  <AlertDescription>{state.error}</AlertDescription>
                </Alert>
              )}

              {state.fieldErrors && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>Validation Error</AlertTitle>
                  <AlertDescription>
                    Please check your input fields for errors.
                  </AlertDescription>
                </Alert>
              )}

              {state.success && state.data && (
                <Tabs defaultValue="output">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="output">Output</TabsTrigger>
                    <TabsTrigger value="stats">Statistics</TabsTrigger>
                    <TabsTrigger value="preview">Preview</TabsTrigger>
                  </TabsList>

                  <TabsContent value="output" className="space-y-4">
                    <div className="flex justify-between items-center">
                      <Label>Formatted Output</Label>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleCopy(state.data?.outputData || '')}
                        >
                          <Copy className="h-4 w-4 mr-1" />
                          Copy
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDownload(state.data?.outputData || '', outputFormat)}
                        >
                          <Download className="h-4 w-4 mr-1" />
                          Download
                        </Button>
                      </div>
                    </div>
                    <Textarea
                      value={state.data.outputData}
                      readOnly
                      className="min-h-[400px] font-mono text-sm"
                    />
                  </TabsContent>

                  <TabsContent value="stats" className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1">
                        <Label className="text-sm text-muted-foreground">Original Length</Label>
                        <p className="text-2xl font-bold">{state.data.statistics.originalLength}</p>
                      </div>
                      <div className="space-y-1">
                        <Label className="text-sm text-muted-foreground">Processed Length</Label>
                        <p className="text-2xl font-bold">{state.data.statistics.processedLength}</p>
                      </div>
                      <div className="space-y-1">
                        <Label className="text-sm text-muted-foreground">Chunks Created</Label>
                        <p className="text-2xl font-bold">{state.data.statistics.chunkCount}</p>
                      </div>
                      <div className="space-y-1">
                        <Label className="text-sm text-muted-foreground">Avg Chunk Size</Label>
                        <p className="text-2xl font-bold">{state.data.statistics.averageChunkSize}</p>
                      </div>
                      <div className="space-y-1">
                        <Label className="text-sm text-muted-foreground">Characters Removed</Label>
                        <p className="text-2xl font-bold">{state.data.statistics.removedCharacters}</p>
                      </div>
                      <div className="space-y-1">
                        <Label className="text-sm text-muted-foreground">Processing Time</Label>
                        <p className="text-2xl font-bold">{state.data.statistics.processingTime}ms</p>
                      </div>
                    </div>

                    {state.data.warnings && state.data.warnings.length > 0 && (
                      <Alert>
                        <AlertTriangle className="h-4 w-4" />
                        <AlertTitle>Warnings</AlertTitle>
                        <AlertDescription>
                          <ul className="list-disc list-inside">
                            {state.data.warnings.map((warning, i) => (
                              <li key={i}>{warning}</li>
                            ))}
                          </ul>
                        </AlertDescription>
                      </Alert>
                    )}
                  </TabsContent>

                  <TabsContent value="preview" className="space-y-4">
                    <Label>Chunk Preview</Label>
                    <div className="space-y-4 max-h-[500px] overflow-y-auto">
                      {state.data.processedChunks.slice(0, 5).map((chunk, i) => (
                        <Card key={chunk.id}>
                          <CardHeader className="pb-3">
                            <div className="flex justify-between items-center">
                              <CardTitle className="text-sm">Chunk {i + 1}</CardTitle>
                              <Badge variant="secondary">{chunk.metadata.wordCount} words</Badge>
                            </div>
                          </CardHeader>
                          <CardContent>
                            <p className="text-sm text-muted-foreground line-clamp-3">
                              {chunk.content}
                            </p>
                            {chunk.metadata.keywords && (
                              <div className="mt-2 flex gap-1 flex-wrap">
                                {chunk.metadata.keywords.map((keyword, j) => (
                                  <Badge key={j} variant="outline" className="text-xs">
                                    {keyword}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      ))}
                      {state.data.processedChunks.length > 5 && (
                        <p className="text-center text-sm text-muted-foreground">
                          ... and {state.data.processedChunks.length - 5} more chunks
                        </p>
                      )}
                    </div>
                  </TabsContent>
                </Tabs>
              )}

              {!state.success && !state.error && !isLoading && (
                <div className="text-center py-10 text-muted-foreground">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Upload a document and configure processing options to see results.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}