"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as React from "react";
import {
  AlertCircleIcon,
  BotIcon,
  CalendarDaysIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  FileTextIcon,
  RefreshCcwIcon,
  SendIcon,
  SparklesIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Field,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  generateAiAdvice,
  sendAiAdviceChat,
} from "@/features/platform/api";
import {
  useAiAdviceCalendarQuery,
  useAiSettingsQuery,
} from "@/features/platform/queries";

const weekLabels = ["一", "二", "三", "四", "五", "六", "日"];

export function AiAdviceView() {
  const queryClient = useQueryClient();
  const [chatPrompt, setChatPrompt] = React.useState("");
  const [selectedDate, setSelectedDate] = React.useState<string | null>(null);
  const [calendarMonth, setCalendarMonth] = React.useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() + 1 };
  });
  const aiCalendarQuery = useAiAdviceCalendarQuery(selectedDate);
  const aiSettingsQuery = useAiSettingsQuery();
  const applyCalendarResponse = React.useCallback(
    (response: Awaited<ReturnType<typeof generateAiAdvice>>) => {
      queryClient.invalidateQueries({ queryKey: ["ai-advice"] });
      if (response.selectedDate) {
        setSelectedDate(response.selectedDate);
        const [year, month] = response.selectedDate.split("-").map(Number);
        setCalendarMonth({ year, month });
      }
    },
    [queryClient]
  );
  const externalMutation = useMutation({
    mutationFn: () => generateAiAdvice(""),
    onSuccess: applyCalendarResponse,
  });
  const chatMutation = useMutation({
    mutationFn: sendAiAdviceChat,
    onSuccess: (response) => {
      setChatPrompt("");
      applyCalendarResponse(response);
    },
  });
  const calendarData = aiCalendarQuery.data;
  const record = calendarData?.record ?? null;
  const savedDates = new Set(calendarData?.dates ?? []);
  const selectedCalendarDate = selectedDate ?? calendarData?.selectedDate ?? null;
  const days = calendarDays(calendarMonth.year, calendarMonth.month);
  const aiReady =
    Boolean(aiSettingsQuery.data?.hasApiKey) &&
    Boolean(aiSettingsQuery.data?.baseUrl) &&
    Boolean(aiSettingsQuery.data?.model);
  const selectedIsToday =
    Boolean(selectedCalendarDate) && selectedCalendarDate === calendarData?.today;
  const aiError =
    externalMutation.error?.message ??
    chatMutation.error?.message ??
    "";
  const retryPending = externalMutation.isPending || chatMutation.isPending;
  const retryLastAiAction = React.useCallback(() => {
    if (externalMutation.error) {
      externalMutation.mutate();
      return;
    }
    if (chatMutation.error) {
      chatMutation.mutate(chatPrompt);
    }
  }, [chatMutation, chatPrompt, externalMutation]);
  const aiStatus = aiReady ? "ready" : "missing-config";
  const aiUnavailableReason = !aiReady
    ? "请先在数据管理补齐 AI Base URL、模型和 API Key。"
    : "";

  return (
    <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_380px]">
      <div className="flex flex-col gap-3">
        <Card>
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2">
              <BotIcon />
              每日 AI 建议
            </CardTitle>
            <CardDescription>按数据管理中的私有数据和 AI 配置生成</CardDescription>
            <CardAction>
              <Badge variant={aiStatus === "ready" ? "secondary" : "outline"}>
                {aiStatus}
              </Badge>
            </CardAction>
          </CardHeader>
          <CardContent className="grid gap-3">
            <Button
              className="w-fit"
              variant="secondary"
              onClick={() => externalMutation.mutate()}
              disabled={!aiReady || externalMutation.isPending}
            >
              <SparklesIcon data-icon="inline-start" />
              {externalMutation.isPending ? "生成中" : "生成每日 AI 建议"}
            </Button>
            {aiUnavailableReason ? (
              <div className="rounded-lg bg-muted/50 p-3 text-sm text-muted-foreground">
                {aiUnavailableReason}
              </div>
            ) : null}
            {aiError ? (
              <div className="flex flex-wrap items-start justify-between gap-3 rounded-lg bg-muted/50 p-3 text-sm text-muted-foreground">
                <div className="flex min-w-0 items-start gap-2">
                  <AlertCircleIcon />
                  <span className="min-w-0">{aiError}</span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={retryLastAiAction}
                  disabled={
                    retryPending ||
                    (Boolean(externalMutation.error) && !aiReady) ||
                    (Boolean(chatMutation.error) &&
                      (!chatPrompt.trim() || !aiReady))
                  }
                >
                  <RefreshCcwIcon data-icon="inline-start" />
                  重试
                </Button>
              </div>
            ) : null}
          </CardContent>
        </Card>
        <Card className="min-w-0">
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2">
              <FileTextIcon />
              AI 日历记录
            </CardTitle>
            <CardDescription>
              {record
                ? `${record.date}，生成时间 ${record.generated_at}`
                : "尚未选择或保存 AI 建议"}
            </CardDescription>
            <CardAction>
              <Badge variant="outline">{record?.source ?? "local"}</Badge>
            </CardAction>
          </CardHeader>
          <CardContent>
            {aiCalendarQuery.isLoading ? (
              <div className="grid gap-2">
                <Skeleton className="h-5 w-1/3" />
                <Skeleton className="h-72 w-full" />
              </div>
            ) : record ? (
              <div className="grid gap-4">
                <div className="rounded-lg bg-muted/50 p-3">
                  <div className="text-sm text-muted-foreground">交易时段</div>
                  <div className="mt-1 text-sm">
                    {record.beijing_context.estimated_session_status ?? "--"}
                  </div>
                  <div className="mt-1 text-sm text-muted-foreground">
                    {record.beijing_context.timing_suggestion ?? ""}
                  </div>
                </div>
                <div className="max-h-[560px] overflow-auto rounded-lg bg-muted/50 p-3">
                  <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed">
                    {record.content}
                  </pre>
                </div>
                {record.messages.length > 1 ? (
                  <div className="grid gap-2">
                    <div className="text-sm font-medium">对话记录</div>
                    <div className="grid gap-2">
                      {record.messages.map((message, index) => (
                        <MessageBubble
                          key={`${message.created_at}-${index}`}
                          role={message.role}
                          content={message.content}
                          createdAt={message.created_at}
                        />
                      ))}
                    </div>
                  </div>
                ) : null}
                {record.news.length ? (
                  <div className="grid gap-2">
                    <div className="text-sm font-medium">保存的新闻标题</div>
                    {record.news.slice(0, 8).map((item) => (
                      <div key={`${item.published}-${item.title}`} className="text-sm">
                        <div>{item.title}</div>
                        <div className="text-xs text-muted-foreground">
                          {item.source} {item.published}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
                {selectedIsToday ? (
                  <FieldGroup>
                    <Field>
                      <FieldLabel htmlFor="ai-chat-prompt">追问</FieldLabel>
                      <Textarea
                        id="ai-chat-prompt"
                        value={chatPrompt}
                        onChange={(event) => setChatPrompt(event.target.value)}
                        className="min-h-24"
                        placeholder="例如：NOK 现在应该继续持有还是减仓？"
                      />
                    </Field>
                    <Button
                      onClick={() => chatMutation.mutate(chatPrompt)}
                      disabled={
                        !aiReady ||
                        !chatPrompt.trim() ||
                        chatMutation.isPending
                      }
                    >
                      <SendIcon data-icon="inline-start" />
                      {chatMutation.isPending ? "发送中" : "发送追问"}
                    </Button>
                    {aiUnavailableReason ? (
                      <div className="rounded-lg bg-muted/50 p-3 text-sm text-muted-foreground">
                        {aiUnavailableReason}
                      </div>
                    ) : null}
                  </FieldGroup>
                ) : null}
              </div>
            ) : (
              <div className="rounded-lg bg-muted/50 p-3 text-sm text-muted-foreground">
                生成今日 AI 建议后，这里会保存记录并开启追问。
              </div>
            )}
          </CardContent>
        </Card>
      </div>
      <div className="flex flex-col gap-3">
        <Card>
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2">
              <CalendarDaysIcon />
              AI建议日历
            </CardTitle>
            <CardDescription>
              每个北京时间自然日保存一条综合建议
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <div className="flex items-center justify-between gap-2">
              <Button
                variant="outline"
                size="icon-sm"
                onClick={() => setCalendarMonth(shiftMonth(calendarMonth, -1))}
              >
                <ChevronLeftIcon />
                <span className="sr-only">上个月</span>
              </Button>
              <div className="text-sm font-medium">
                {calendarMonth.year} 年 {calendarMonth.month} 月
              </div>
              <Button
                variant="outline"
                size="icon-sm"
                onClick={() => setCalendarMonth(shiftMonth(calendarMonth, 1))}
              >
                <ChevronRightIcon />
                <span className="sr-only">下个月</span>
              </Button>
            </div>
            <div className="grid grid-cols-7 gap-1 text-center text-xs text-muted-foreground">
              {weekLabels.map((label) => (
                <div key={label}>{label}</div>
              ))}
            </div>
            <div className="grid grid-cols-7 gap-1">
              {days.map((day, index) =>
                day ? (
                  <Button
                    key={day}
                    variant={day === selectedCalendarDate ? "secondary" : "outline"}
                    size="sm"
                    disabled={!savedDates.has(day)}
                    onClick={() => setSelectedDate(day)}
                    className="h-9 px-1"
                  >
                    {Number(day.slice(-2))}
                    {savedDates.has(day) ? " ●" : ""}
                  </Button>
                ) : (
                  <div key={`empty-${index}`} className="h-9" />
                )
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MessageBubble({
  role,
  content,
  createdAt,
}: {
  role: "user" | "assistant";
  content: string;
  createdAt: string;
}) {
  const isUser = role === "user";
  return (
    <div className={isUser ? "flex justify-end" : "flex justify-start"}>
      <div
        className={
          isUser
            ? "max-w-[82%] rounded-lg bg-primary p-3 text-primary-foreground"
            : "max-w-[82%] rounded-lg bg-muted p-3"
        }
      >
        <div className="whitespace-pre-wrap text-sm leading-relaxed">{content}</div>
        <div className="mt-2 text-xs opacity-70">{createdAt}</div>
      </div>
    </div>
  );
}

function calendarDays(year: number, month: number) {
  const first = new Date(year, month - 1, 1);
  const last = new Date(year, month, 0);
  const leading = (first.getDay() + 6) % 7;
  const days: Array<string | null> = Array.from({ length: leading }, () => null);
  for (let day = 1; day <= last.getDate(); day += 1) {
    days.push(formatDate(year, month, day));
  }
  while (days.length % 7 !== 0) {
    days.push(null);
  }
  return days;
}

function shiftMonth(
  value: { year: number; month: number },
  offset: number
) {
  const next = new Date(value.year, value.month - 1 + offset, 1);
  return { year: next.getFullYear(), month: next.getMonth() + 1 };
}

function formatDate(year: number, month: number, day: number) {
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(
    2,
    "0"
  )}`;
}
