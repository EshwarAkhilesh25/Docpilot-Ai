import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Menu,
  Upload,
  FileText,
  Plus,
  X as XIcon,
  MessageSquare,
  SquarePen,
} from "lucide-react";
import { DashboardLayout } from "@components/layout/DashboardLayout";
import { ConversationSidebar } from "@components/chat/ConversationSidebar";
import { MessageList } from "@components/chat/MessageList";
import { MessageInput } from "@components/chat/MessageInput";
import { isAxiosError } from "axios";
import { EmptyState } from "@components/chat/EmptyState";
import { SourcesPanel, DocumentSource } from "@components/chat/SourcesPanel";
import { DocumentLibraryModal } from "@components/chat/DocumentLibraryModal";
import { ErrorBoundary } from "@components/common/ErrorBoundary";
import { PremiumBackground } from "@components/common/PremiumBackground";
import {
  useChat,
  useConversations,
  useConversation,
  useDeleteConversation,
  useUpdateConversation,
} from "@hooks/useChat";
import { useDocuments } from "@hooks/useDocuments";
import { DocumentSummary } from "@services/documentService";
import {
  ConversationMessage,
  MessageRole,
  MessageStatus,
} from "@services/chatService";
import { pageTransition } from "@lib/animations";
import { useSearchParams, useNavigate, useLocation } from "react-router-dom";
import { useUIStore } from "@store/uiStore";

export default function Chat() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [optimisticMessages, setOptimisticMessages] = useState<
    ConversationMessage[]
  >([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>(() =>
    searchParams.getAll("document"),
  );
  const [isSourcesPanelOpen, setIsSourcesPanelOpen] = useState(false);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [showDocumentLibrary, setShowDocumentLibrary] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const intentHandledRef = useRef(false);

  // Handle URL parameter for pre-selected document or session
  useEffect(() => {
    const sessionId = searchParams.get("session");

    if (sessionId) {
      setActiveSessionId(sessionId);
      navigate("/chat", { replace: true, state: location.state });
    }
  }, [searchParams, navigate, location.state]);

  const {
    data: conversations,
    isLoading: isLoadingConversations,
    error: conversationsError,
  } = useConversations();
  const { data: conversationDetail, isError: isConversationError } =
    useConversation(activeSessionId || "", !!activeSessionId);
  const chatMutation = useChat();
  const updateMutation = useUpdateConversation();
  const deleteMutation = useDeleteConversation();

  // Fetch real documents from documents API
  const { data: documentsResponse } = useDocuments();
  const documents =
    (documentsResponse as { items?: DocumentSummary[] })?.items || [];
  const hasDocuments = documents.length > 0;

  // Mock sources for panel (replace with real data from chat response)
  const sources: DocumentSource[] = [
    {
      id: "550e8400-e29b-41d4-a716-446655440001",
      original_filename: "report.pdf",
      file_type: "pdf",
      uploaded_at: new Date().toISOString(),
    },
    {
      id: "550e8400-e29b-41d4-a716-446655440002",
      original_filename: "presentation.pptx",
      file_type: "pptx",
      uploaded_at: new Date().toISOString(),
    },
  ];

  // Combine server messages with optimistic messages
  // Filter out any optimistic messages that might duplicate server messages
  // Force allMessages to be empty if activeSessionId is null to prevent React Query from retaining stale data
  const allMessages = activeSessionId ? conversationDetail?.messages || [] : [];
  const displayMessages = [
    ...allMessages,
    ...optimisticMessages.filter(
      (msg) =>
        !allMessages.some(
          (serverMsg) =>
            serverMsg.role === msg.role &&
            serverMsg.content === msg.content &&
            Math.abs(
              new Date(serverMsg.created_at).getTime() -
                new Date(msg.created_at).getTime(),
            ) < 1000,
        ),
    ),
  ];

  // Load conversation history when switching - keep previous visible while loading
  const handleSelectConversation = useCallback((sessionId: string) => {
    setActiveSessionId(sessionId);
    setOptimisticMessages([]); // Clear optimistic messages when switching
    setError(null);
    setIsSidebarOpen(false); // Close sidebar on mobile after selection
  }, []);

  // Start new conversation and focus input
  const handleNewConversation = useCallback(() => {
    setActiveSessionId(null);
    setOptimisticMessages([]);
    setError(null);
    setIsSidebarOpen(false);
    // Focus input after state update
    setTimeout(() => {
      inputRef.current?.focus();
    }, 0);
  }, []);

  // Delete conversation
  const handleDeleteConversation = useCallback(
    (sessionId: string) => {
      deleteMutation.mutate(sessionId, {
        onSuccess: () => {
          if (activeSessionId === sessionId) {
            handleNewConversation();
          }
        },
        onError: () => {
          setError("Failed to delete conversation");
        },
      });
    },
    [activeSessionId, deleteMutation, handleNewConversation],
  );

  // Send message with optimistic update
  const handleSendMessage = useCallback(
    async (content: string, intent?: string) => {
      const tempId = `temp-${Date.now()}`;

      // Add optimistic user message with SENDING status
      const optimisticMessage: ConversationMessage = {
        id: tempId,
        role: MessageRole.USER,
        content,
        created_at: new Date().toISOString(),
        status: MessageStatus.SENDING,
      };
      setOptimisticMessages((prev: ConversationMessage[]) => [
        ...prev,
        optimisticMessage,
      ]);
      setIsTyping(true);
      setError(null);

      const noticeId = `starting-notice-${tempId}`;
      const startupTimer = setTimeout(() => {
        if (!useUIStore.getState().hasBackendResponded) {
          setOptimisticMessages((prev: ConversationMessage[]) => [
            ...prev,
            {
              id: noticeId,
              session_id: activeSessionId || "",
              role: MessageRole.ASSISTANT,
              content:
                "⏳ Starting AI services...\n\nYour first response may take up to a minute.",
              status: MessageStatus.SENT,
              created_at: new Date().toISOString(),
            },
          ]);
        }
      }, 3500);

      try {
        const response = await chatMutation.mutateAsync({
          question: content,
          session_id: activeSessionId || undefined,
          document_ids: activeSessionId
            ? undefined
            : selectedDocumentIds.length > 0
              ? selectedDocumentIds
              : undefined,
          intent: intent,
        });

        // Update session ID if new conversation
        if (!activeSessionId && response.session_id) {
          setActiveSessionId(response.session_id);
        }

        // Remove optimistic message (server will have the real message)
        setOptimisticMessages((prev: ConversationMessage[]) =>
          prev.filter(
            (m: ConversationMessage) => m.id !== tempId && m.id !== noticeId,
          ),
        );
      } catch (e: unknown) {
        // Update optimistic message to FAILED status
        setOptimisticMessages((prev: ConversationMessage[]) =>
          prev
            .filter((m: ConversationMessage) => m.id !== noticeId)
            .map((m: ConversationMessage) =>
              m.id === tempId ? { ...m, status: MessageStatus.FAILED } : m,
            ),
        );

        const err = e as Error;
        // Check if error is due to missing vector index
        if (
          isAxiosError(err) &&
          err.response?.data?.detail?.includes("Index has not been created")
        ) {
          setError(
            "Please upload and process a document first before using chat.",
          );
        } else {
          setError("Failed to send message. Please try again.");
        }
      } finally {
        clearTimeout(startupTimer);
        setIsTyping(false);
      }
    },
    [activeSessionId, chatMutation, selectedDocumentIds],
  );

  // Retry failed message - mutate status instead of removing
  const handleRetryMessage = useCallback(
    (message: ConversationMessage) => {
      // Update status from FAILED to SENDING
      setOptimisticMessages((prev: ConversationMessage[]) =>
        prev.map((m: ConversationMessage) =>
          m.id === message.id ? { ...m, status: MessageStatus.SENDING } : m,
        ),
      );
      setIsTyping(true);
      setError(null);

      // Resend the same message content
      chatMutation
        .mutateAsync({
          question: message.content,
          session_id: activeSessionId || undefined,
        })
        .then((response) => {
          // Update session ID if new conversation
          if (!activeSessionId && response.session_id) {
            setActiveSessionId(response.session_id);
          }

          // Remove optimistic message (server will have the real message)
          setOptimisticMessages((prev: ConversationMessage[]) =>
            prev.filter((m: ConversationMessage) => m.id !== message.id),
          );

          // Don't add assistant message to optimistic messages
          // The conversation detail will be updated by the server with the real message
          // This prevents duplication when the server response arrives
        })
        .catch(() => {
          // Update back to FAILED status
          setOptimisticMessages((prev: ConversationMessage[]) =>
            prev.map((m: ConversationMessage) =>
              m.id === message.id ? { ...m, status: MessageStatus.FAILED } : m,
            ),
          );
          setError("Failed to send message. Please try again.");
        })
        .finally(() => {
          setIsTyping(false);
        });
    },
    [activeSessionId, chatMutation],
  );

  // Empty state - show document selection if no documents attached
  const showEmptyState =
    displayMessages.length === 0 && !isTyping && !activeSessionId;
  const showDocumentSelectionScreen =
    showEmptyState && selectedDocumentIds.length === 0;

  // Handle suggested prompt selection
  const handleSelectPrompt = useCallback(
    (prompt: string) => {
      handleSendMessage(prompt);
    },
    [handleSendMessage],
  );

  // Handle incoming intent from navigation state
  useEffect(() => {
    if (
      location.state?.intent &&
      location.state?.prompt &&
      !activeSessionId &&
      !isTyping &&
      !intentHandledRef.current
    ) {
      intentHandledRef.current = true;
      handleSendMessage(location.state.prompt, location.state.intent);

      // Clear the state so it doesn't trigger again on refresh
      window.history.replaceState({}, document.title);
    }
  }, [location.state, activeSessionId, isTyping, handleSendMessage]);

  // Handle source click - scroll to first citation
  const handleSourceClick = useCallback((sourceId: string) => {
    const firstCitationId = `citation-${sourceId}-0`;
    const element = document.getElementById(firstCitationId);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
      // Highlight the citation briefly
      element.classList.add("ring-2", "ring-primary", "ring-offset-2");
      setTimeout(() => {
        element.classList.remove("ring-2", "ring-primary", "ring-offset-2");
      }, 2000);
    }
  }, []);

  // Get the effective document IDs for the current context
  const currentDocumentIds = useMemo(() => {
    return activeSessionId && conversationDetail
      ? conversationDetail.document_ids || []
      : selectedDocumentIds;
  }, [activeSessionId, conversationDetail, selectedDocumentIds]);

  // Handle document selection from library
  const handleSelectDocumentFromLibrary = useCallback(
    (documentId: string) => {
      if (activeSessionId) {
        if (!currentDocumentIds.includes(documentId)) {
          updateMutation.mutate({
            sessionId: activeSessionId,
            data: { document_ids: [...currentDocumentIds, documentId] },
          });
        }
      } else {
        if (!selectedDocumentIds.includes(documentId)) {
          setSelectedDocumentIds([...selectedDocumentIds, documentId]);
        }
      }
      setShowDocumentLibrary(false);
    },
    [activeSessionId, currentDocumentIds, selectedDocumentIds, updateMutation],
  );

  // Handle removing attached document
  const handleRemoveDocument = useCallback(
    (documentId: string) => {
      if (activeSessionId) {
        updateMutation.mutate({
          sessionId: activeSessionId,
          data: {
            document_ids: currentDocumentIds.filter((id) => id !== documentId),
          },
        });
      } else {
        setSelectedDocumentIds(
          selectedDocumentIds.filter((id) => id !== documentId),
        );
      }
    },
    [activeSessionId, currentDocumentIds, selectedDocumentIds, updateMutation],
  );

  // Handle upload navigation
  const handleUploadDocument = useCallback(() => {
    navigate("/upload");
  }, [navigate]);

  // Get attached document objects
  const attachedDocuments = documents.filter((doc) =>
    currentDocumentIds.includes(doc.id),
  );

  // Dynamic summarization prompt based on attached documents
  const getSummarizePrompt = useCallback(() => {
    if (attachedDocuments.length === 0) return "Summarize this document";
    if (attachedDocuments.length === 1) {
      return `Summarize ${attachedDocuments[0].original_filename}`;
    }
    return "Summarize all attached documents";
  }, [attachedDocuments]);

  return (
    <DashboardLayout fullHeight>
      <PremiumBackground variant="subtle" />
      <ErrorBoundary>
        <motion.div
          className="h-full flex"
          variants={pageTransition}
          initial="hidden"
          animate="visible"
          exit="hidden"
        >
          {/* Sidebar */}
          <div
            className={`
              fixed inset-0 z-40 lg:relative lg:z-0
              ${isSidebarOpen ? "block" : "hidden lg:block"}
            `}
          >
            <div
              className="absolute inset-0 lg:hidden bg-black/50"
              onClick={() => setIsSidebarOpen(false)}
            />
            <ConversationSidebar
              conversations={conversations || []}
              activeSessionId={activeSessionId}
              isLoading={isLoadingConversations}
              error={conversationsError ? "Failed to load conversations" : null}
              onSelectConversation={handleSelectConversation}
              onNewConversation={handleNewConversation}
              onDeleteConversation={handleDeleteConversation}
              onCloseSidebar={() => setIsSidebarOpen(false)}
            />
          </div>

          {/* Chat Area */}
          <div className="flex-1 flex flex-col h-full bg-background relative overflow-hidden min-w-0">
            {/* Header */}
            <header className="flex items-center justify-between px-4 py-4 border-b border-border bg-card shrink-0 relative z-10">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setIsSidebarOpen(true)}
                  className="lg:hidden p-2 -ml-2 rounded-lg hover:bg-muted text-foreground transition-colors touch-target"
                  aria-label="Open conversations"
                >
                  <Menu className="w-5 h-5" />
                </button>
                <h1 className="text-xl font-semibold text-foreground">
                  AI Workspace
                </h1>
              </div>
              <button
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  handleNewConversation();
                }}
                className="lg:hidden touch-target p-2 -mr-2 rounded-lg text-primary hover:bg-primary/10 transition-colors relative z-20 cursor-pointer"
                aria-label="New conversation"
              >
                <SquarePen className="w-6 h-6" />
              </button>
            </header>

            {/* Messages */}
            {isConversationError ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center overflow-y-auto">
                <div className="inline-flex p-4 rounded-full bg-destructive/10 text-destructive mb-4">
                  <MessageSquare className="h-8 w-8" />
                </div>
                <h3 className="text-xl font-medium text-foreground mb-2">
                  Conversation Unavailable
                </h3>
                <p className="text-muted-foreground max-w-md">
                  This conversation could not be loaded. It may have been
                  deleted or the server restarted.
                </p>
                <button
                  onClick={handleNewConversation}
                  className="mt-6 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                >
                  Start New Conversation
                </button>
              </div>
            ) : showDocumentSelectionScreen ? (
              <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-8 overflow-y-auto">
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="max-w-2xl w-full flex flex-col items-center text-center"
                >
                  <div className="mb-6">
                    <div className="inline-flex p-5 rounded-full bg-primary/10 text-primary mb-4">
                      <FileText className="h-10 w-10 sm:h-12 sm:w-12" />
                    </div>
                    <h2 className="text-2xl sm:text-3xl font-semibold text-foreground mb-3 tracking-tight">
                      Welcome to AI Copilot
                    </h2>
                    <p className="text-muted-foreground text-sm sm:text-base max-w-md mx-auto">
                      Upload a document or choose one from your Knowledge
                      Library to start asking questions.
                    </p>
                  </div>

                  <div className="flex flex-col sm:flex-row gap-3 w-full max-w-md mx-auto">
                    <button
                      onClick={handleUploadDocument}
                      className="touch-target flex-1 flex items-center justify-center gap-3 p-4 rounded-xl border border-border bg-card hover:border-primary hover:bg-primary/5 transition-all group shadow-sm"
                    >
                      <Upload className="h-5 w-5 text-primary" />
                      <span className="font-medium text-foreground">
                        Import
                      </span>
                    </button>

                    <button
                      onClick={() => setShowDocumentLibrary(true)}
                      disabled={!hasDocuments}
                      className="touch-target flex-1 flex items-center justify-center gap-3 p-4 rounded-xl border border-border bg-card hover:border-primary hover:bg-primary/5 transition-all group disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                    >
                      <FileText className="h-5 w-5 text-primary" />
                      <span className="font-medium text-foreground">
                        Library
                      </span>
                    </button>
                  </div>
                </motion.div>
              </div>
            ) : showEmptyState ? (
              <EmptyState
                onSelectPrompt={handleSelectPrompt}
                hasDocuments={hasDocuments}
                summarizePrompt={getSummarizePrompt()}
                className="flex-1 overflow-y-auto pt-8 pb-4"
              />
            ) : (
              <MessageList
                messages={displayMessages}
                isTyping={isTyping}
                onRetry={handleRetryMessage}
                className="flex-1 min-h-0"
              />
            )}

            {/* Error Display */}
            {error && (
              <div className="px-4 py-2 bg-destructive/10 text-destructive text-sm text-center shrink-0">
                {error}
              </div>
            )}

            {/* Attached Documents Display */}
            {attachedDocuments.length > 0 && (
              <div className="px-4 py-2 border-t bg-muted/30 shrink-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-medium text-muted-foreground">
                    Attached:
                  </span>
                  <AnimatePresence>
                    {attachedDocuments.map((doc) => (
                      <motion.div
                        key={doc.id}
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className="flex items-center gap-2 px-3 py-1.5 bg-primary/10 border border-primary/20 rounded-full text-sm"
                      >
                        <FileText className="w-3 h-3 text-primary" />
                        <span className="text-foreground truncate max-w-[150px]">
                          {doc.original_filename}
                        </span>
                        <button
                          onClick={() => handleRemoveDocument(doc.id)}
                          className="text-muted-foreground hover:text-foreground transition-colors"
                        >
                          <XIcon className="w-3 h-3" />
                        </button>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                  <button
                    onClick={() => setShowDocumentLibrary(true)}
                    className="flex items-center gap-1 px-2 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <Plus className="w-3 h-3" />
                    Add
                  </button>
                </div>
              </div>
            )}

            {/* Input */}
            <MessageInput
              ref={inputRef}
              onSend={handleSendMessage}
              disabled={
                isTyping ||
                chatMutation.isPending ||
                (!activeSessionId && selectedDocumentIds.length === 0)
              }
              placeholder={
                !activeSessionId && selectedDocumentIds.length === 0
                  ? "Select documents to start chatting..."
                  : showEmptyState
                    ? "Ask anything about your documents..."
                    : "Type your message..."
              }
            />

            {/* Sources Panel */}
            <SourcesPanel
              sources={sources}
              selectedSourceId={selectedSourceId}
              onSourceSelect={setSelectedSourceId}
              onSourceClick={handleSourceClick}
              isOpen={isSourcesPanelOpen}
              onClose={() => setIsSourcesPanelOpen(false)}
            />

            {/* Document Library Modal */}
            <DocumentLibraryModal
              isOpen={showDocumentLibrary}
              onClose={() => setShowDocumentLibrary(false)}
              documents={documents}
              selectedIds={currentDocumentIds}
              onSelectDocument={handleSelectDocumentFromLibrary}
            />
          </div>
        </motion.div>
      </ErrorBoundary>
    </DashboardLayout>
  );
}
