"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { adminApi, type AdminOption, type AdminQuestion } from "@/api/admin/admin.api";
import { useBackendToken } from "@/hooks/use-backend-token";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const errMsg = (e: unknown) => (e instanceof Error ? e.message : "Error");

function useRefresh(key: string) {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["admin", key] });
}

function OptionsTab({ token }: { token: string }) {
  const refresh = useRefresh("options");
  const { data = [], error } = useQuery({
    queryKey: ["admin", "options"],
    queryFn: () => adminApi.options(token),
    enabled: !!token,
  });
  const [draft, setDraft] = useState({
    category: "level",
    key: "",
    label: "",
    icon: "Circle",
    sortOrder: 0,
  });

  const create = useMutation({
    mutationFn: () =>
      adminApi.createOption(token, {
        ...draft,
        category: draft.category as AdminOption["category"],
      }),
    onSuccess: () => {
      toast.success("Option created");
      refresh();
    },
    onError: (e) => toast.error(errMsg(e)),
  });
  const remove = useMutation({
    mutationFn: (id: number) => adminApi.deleteOption(token, id),
    onSuccess: () => {
      toast.success("Option deleted");
      refresh();
    },
    onError: (e) => toast.error(errMsg(e)),
  });

  return (
    <div className="space-y-4">
      {error && <p className="text-destructive">{errMsg(error)}</p>}
      <div className="grid grid-cols-2 gap-2 md:grid-cols-6">
        <select
          className="rounded-md border bg-background px-2 text-sm"
          value={draft.category}
          onChange={(e) => setDraft({ ...draft, category: e.target.value })}
        >
          <option value="level">level</option>
          <option value="position">position</option>
          <option value="focus">focus</option>
        </select>
        <Input placeholder="key" value={draft.key} onChange={(e) => setDraft({ ...draft, key: e.target.value })} />
        <Input placeholder="label" value={draft.label} onChange={(e) => setDraft({ ...draft, label: e.target.value })} />
        <Input placeholder="icon" value={draft.icon} onChange={(e) => setDraft({ ...draft, icon: e.target.value })} />
        <Input
          type="number"
          placeholder="order"
          value={draft.sortOrder}
          onChange={(e) => setDraft({ ...draft, sortOrder: Number(e.target.value) })}
        />
        <Button onClick={() => create.mutate()} disabled={create.isPending || !draft.key || !draft.label}>
          Add
        </Button>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Category</TableHead>
            <TableHead>Key</TableHead>
            <TableHead>Label</TableHead>
            <TableHead>Order</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((o) => (
            <TableRow key={o.ID}>
              <TableCell>{o.category}</TableCell>
              <TableCell>{o.key}</TableCell>
              <TableCell>{o.label}</TableCell>
              <TableCell>{o.sortOrder}</TableCell>
              <TableCell>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => confirm(`Delete "${o.label}"?`) && remove.mutate(o.ID)}
                >
                  Delete
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function QuestionRow({ q, token }: { q: AdminQuestion; token: string }) {
  const refresh = useRefresh("questions");
  const [editing, setEditing] = useState(false);
  const [question, setQuestion] = useState(q.question);
  const [criteria, setCriteria] = useState(q.criteria);
  const done = (msg: string) => () => {
    toast.success(msg);
    setEditing(false);
    refresh();
  };
  const toggle = useMutation({
    mutationFn: () => adminApi.updateQuestion(token, q.id, { active: !q.active }),
    onSuccess: done(q.active ? "Deactivated" : "Activated"),
    onError: (e) => toast.error(errMsg(e)),
  });
  const save = useMutation({
    mutationFn: () => adminApi.updateQuestion(token, q.id, { question, criteria }),
    onSuccess: done("Saved"),
    onError: (e) => toast.error(errMsg(e)),
  });
  const newVersion = useMutation({
    mutationFn: () => adminApi.newQuestionVersion(token, { sourceId: q.id, question, criteria }),
    onSuccess: done("New version created"),
    onError: (e) => toast.error(errMsg(e)),
  });

  return (
    <TableRow>
      <TableCell className="whitespace-nowrap">
        {q.focus} · {q.language} · #{q.topicIndex}
        <br />
        <span className="text-xs text-muted-foreground">{q.key} v{q.version}</span>
      </TableCell>
      <TableCell className="min-w-[320px]">
        {editing ? (
          <div className="space-y-2">
            <Textarea value={question} onChange={(e) => setQuestion(e.target.value)} />
            <Textarea value={criteria} onChange={(e) => setCriteria(e.target.value)} />
            <div className="flex gap-2">
              <Button size="sm" onClick={() => save.mutate()}>Save in place</Button>
              <Button size="sm" variant="secondary" onClick={() => newVersion.mutate()}>
                Save as new version
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
            </div>
          </div>
        ) : (
          q.question
        )}
      </TableCell>
      <TableCell>{q.active ? "active" : "inactive"}</TableCell>
      <TableCell className="space-x-2 whitespace-nowrap">
        <Button size="sm" variant="outline" onClick={() => setEditing(true)}>Edit</Button>
        <Button size="sm" variant="outline" onClick={() => toggle.mutate()}>
          {q.active ? "Deactivate" : "Activate"}
        </Button>
      </TableCell>
    </TableRow>
  );
}

function QuestionsTab({ token }: { token: string }) {
  const [language, setLanguage] = useState("");
  const [focus, setFocus] = useState("");
  const { data = [], error } = useQuery({
    queryKey: ["admin", "questions", language, focus],
    queryFn: () => adminApi.questions(token, { language, focus }),
    enabled: !!token,
  });
  return (
    <div className="space-y-4">
      {error && <p className="text-destructive">{errMsg(error)}</p>}
      <div className="flex gap-2">
        <Input className="w-32" placeholder="language (uk/en)" value={language} onChange={(e) => setLanguage(e.target.value)} />
        <Input className="w-48" placeholder="focus" value={focus} onChange={(e) => setFocus(e.target.value)} />
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Topic</TableHead>
            <TableHead>Question</TableHead>
            <TableHead>Status</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((q) => (
            <QuestionRow key={q.id} q={q} token={token} />
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function OutboxTab({ token }: { token: string }) {
  const refresh = useRefresh("outbox");
  const [pending, setPending] = useState(true);
  const { data = [], error } = useQuery({
    queryKey: ["admin", "outbox", pending],
    queryFn: () => adminApi.outbox(token, pending),
    enabled: !!token,
  });
  const retry = useMutation({
    mutationFn: (id: string) => adminApi.retryOutbox(token, id),
    onSuccess: () => {
      toast.success("Queued for retry");
      refresh();
    },
    onError: (e) => toast.error(errMsg(e)),
  });
  return (
    <div className="space-y-4">
      {error && <p className="text-destructive">{errMsg(error)}</p>}
      <Button variant="outline" size="sm" onClick={() => setPending(!pending)}>
        {pending ? "Showing: unpublished" : "Showing: all"}
      </Button>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Interview</TableHead>
            <TableHead>Published</TableHead>
            <TableHead>Attempts</TableHead>
            <TableHead>Last error</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((e) => (
            <TableRow key={e.interviewId}>
              <TableCell className="font-mono text-xs">{e.interviewId}</TableCell>
              <TableCell>{e.published ? "yes" : "no"}</TableCell>
              <TableCell>{e.attempts}</TableCell>
              <TableCell className="max-w-xs truncate">{e.lastError ?? "—"}</TableCell>
              <TableCell>
                <Button size="sm" variant="outline" onClick={() => retry.mutate(e.interviewId)}>
                  Retry
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export function AdminPage() {
  const token = useBackendToken();
  return (
    <main className="container mx-auto px-6 pb-16 pt-28">
      <h1 className="mb-6 text-3xl font-display font-bold">Admin</h1>
      <Tabs defaultValue="options">
        <TabsList>
          <TabsTrigger value="options">Options</TabsTrigger>
          <TabsTrigger value="questions">Questions</TabsTrigger>
          <TabsTrigger value="outbox">Feedback outbox</TabsTrigger>
        </TabsList>
        <TabsContent value="options"><OptionsTab token={token} /></TabsContent>
        <TabsContent value="questions"><QuestionsTab token={token} /></TabsContent>
        <TabsContent value="outbox"><OutboxTab token={token} /></TabsContent>
      </Tabs>
    </main>
  );
}
