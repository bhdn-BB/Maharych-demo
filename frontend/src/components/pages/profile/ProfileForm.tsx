"use client";

import { useEffect, useMemo, useRef, useState, type DragEvent, type FormEvent } from "react";
import { useSession } from "next-auth/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import Link from "next/link";
import { ArrowRight, CheckCircle2, FileUp, Loader2, X } from "lucide-react";
import { useProfile } from "@/hooks/use-profile";
import { profileApi } from "@/api/profile/profile.api";
import type { CandidateProfile } from "@/api/profile/profile.types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";

const emptyProfile: CandidateProfile = {
  name: "",
  surname: "",
  phoneNumber: "",
  linkedInUrl: "",
  githubUrl: "",
  yearsOfExperience: 0,
  techStack: [],
  resume: "",
};

const RESUME_ACCEPT =
  ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

function splitSkills(value: string) {
  return value.split(",").map((skill) => skill.trim()).filter(Boolean);
}

function Required() {
  return <span aria-hidden="true" className="text-primary"> *</span>;
}

export function ProfileForm() {
  const { data: session, status } = useSession();
  const token = session?.backendToken ?? "";
  const userId = session?.user?.id;
  const queryClient = useQueryClient();
  const [profile, setProfile] = useState<CandidateProfile>(emptyProfile);
  const [skills, setSkills] = useState("");
  const [parsing, setParsing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(0);
  const [fileName, setFileName] = useState("");
  const [dragging, setDragging] = useState(false);
  const uploadRef = useRef<AbortController | null>(null);

  const { data, isPending, isError, refetch } = useProfile();

  useEffect(() => {
    if (data) {
      setProfile(data);
      setSkills(data.techStack.join(", "));
    }
  }, [data]);

  useEffect(() => () => uploadRef.current?.abort(), []);

  const dirty = useMemo(() => {
    const saved = data ?? emptyProfile;
    const current = { ...profile, techStack: splitSkills(skills) };
    return JSON.stringify(current) !== JSON.stringify({ ...saved, techStack: saved.techStack });
  }, [data, profile, skills]);

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const save = useMutation({
    mutationFn: (value: CandidateProfile) => profileApi.put(value, token),
    onSuccess: (saved) => {
      queryClient.setQueryData(["profile", userId], saved);
      toast.success("Profile saved");
    },
    onError: (error) => toast.error(error.message),
  });

  const update = (field: keyof CandidateProfile, value: string | number) => {
    setProfile((current) => ({ ...current, [field]: value }));
  };

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    save.mutate({ ...profile, techStack: splitSkills(skills) });
  };

  const onResumeFile = async (file?: File) => {
    if (!file || parsing) return;
    const previous = profile.resume;
    const controller = new AbortController();
    uploadRef.current = controller;
    setParsing(true);
    setUploadProgress(0);
    setFileName("");
    try {
      const text = await profileApi.parseResume(file, token, setUploadProgress, controller.signal);
      update("resume", text);
      setFileName(file.name);
      toast.success("Resume read. Review the text below, then save your profile.", {
        action: previous.trim()
          ? { label: "Undo", onClick: () => update("resume", previous) }
          : undefined,
      });
    } catch (error) {
      if (!controller.signal.aborted) {
        toast.error(error instanceof Error ? error.message : "Could not read the resume.");
      }
    } finally {
      if (uploadRef.current === controller) uploadRef.current = null;
      setParsing(false);
    }
  };

  const onDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setDragging(false);
    void onResumeFile(event.dataTransfer.files?.[0]);
  };

  if (status === "loading" || (token && isPending)) {
    return (
      <div className="glass rounded-3xl p-6 md:p-8 space-y-5" aria-busy="true" aria-label="Loading profile">
        <Skeleton className="h-4 w-2/3" />
        <div className="grid gap-5 sm:grid-cols-2">
          {Array.from({ length: 6 }, (_, i) => <Skeleton key={i} className="h-10" />)}
        </div>
        <Skeleton className="h-32" />
      </div>
    );
  }
  if (!token) {
    return (
      <div className="glass rounded-3xl p-6 md:p-8 space-y-4">
        <p>Sign in to edit your candidate profile.</p>
        <Button asChild><Link href="/login">Sign in</Link></Button>
      </div>
    );
  }
  if (isError) {
    return (
      <div role="alert" className="glass rounded-3xl p-6 md:p-8 space-y-4">
        <p>Could not load your profile.</p>
        <Button variant="outline" onClick={() => void refetch()}>Try again</Button>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="glass rounded-3xl p-6 md:p-8 space-y-6">
      <p className="text-sm text-muted-foreground">
        These details help tailor your interview questions. Fields marked <span className="text-primary">*</span> are required.
      </p>

      <fieldset className="grid gap-5 sm:grid-cols-2">
        <legend className="sr-only">Personal details</legend>
        <label className="space-y-2 text-sm font-medium">
          <span>First name<Required /></span>
          <Input autoComplete="given-name" value={profile.name} onChange={(e) => update("name", e.target.value)} minLength={2} maxLength={50} required />
        </label>
        <label className="space-y-2 text-sm font-medium">
          <span>Last name<Required /></span>
          <Input autoComplete="family-name" value={profile.surname} onChange={(e) => update("surname", e.target.value)} minLength={2} maxLength={50} required />
        </label>
        <label className="space-y-2 text-sm font-medium">
          <span>Phone number<Required /></span>
          <Input type="tel" autoComplete="tel" inputMode="tel" placeholder="+380 67 123 4567" value={profile.phoneNumber} onChange={(e) => update("phoneNumber", e.target.value)} minLength={10} maxLength={20} required />
        </label>
        <label className="space-y-2 text-sm font-medium">
          <span>Years of experience<Required /></span>
          <Input type="number" inputMode="numeric" min={0} max={50} value={profile.yearsOfExperience} onChange={(e) => update("yearsOfExperience", e.target.value === "" ? 0 : Number(e.target.value))} required />
        </label>
        <label className="space-y-2 text-sm font-medium">
          <span>LinkedIn URL</span>
          <Input type="url" autoComplete="url" placeholder="https://linkedin.com/in/…" value={profile.linkedInUrl} onChange={(e) => update("linkedInUrl", e.target.value)} />
        </label>
        <label className="space-y-2 text-sm font-medium">
          <span>GitHub URL</span>
          <Input type="url" placeholder="https://github.com/…" value={profile.githubUrl} onChange={(e) => update("githubUrl", e.target.value)} />
        </label>
      </fieldset>

      <label className="block space-y-2 text-sm font-medium">
        <span>Technology stack</span>
        <Input value={skills} onChange={(e) => setSkills(e.target.value)} placeholder="Go, PostgreSQL, React" aria-describedby="skills-hint" />
        <span id="skills-hint" className="block text-xs font-normal text-muted-foreground">Separate technologies with commas.</span>
      </label>

      <section aria-labelledby="resume-heading" className="space-y-3">
        <h2 id="resume-heading" className="text-sm font-medium">Resume <span className="font-normal text-muted-foreground">(optional)</span></h2>

        {parsing ? (
          <div role="status" aria-live="polite" className="space-y-3 rounded-xl border border-primary/30 bg-primary/5 p-4 text-sm">
            <div className="flex items-center justify-between gap-3">
              <p className="flex items-center gap-2">
                <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin text-primary" />
                {uploadProgress === null ? "Extracting text from your resume…" : `Uploading resume… ${uploadProgress}%`}
              </p>
              <Button type="button" variant="ghost" size="sm" onClick={() => uploadRef.current?.abort()}>
                <X aria-hidden="true" className="mr-1 h-4 w-4" /> Cancel
              </Button>
            </div>
            {uploadProgress === null
              ? <progress className="h-2 w-full accent-primary" aria-label="Extracting resume text" />
              : <progress className="h-2 w-full accent-primary" aria-label="Uploading resume" value={uploadProgress} max={100} />}
          </div>
        ) : (
          <label
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-6 text-center text-sm transition-colors focus-within:ring-2 focus-within:ring-primary ${dragging ? "border-primary bg-primary/10" : "border-primary/25 bg-primary/5 hover:border-primary/50 hover:bg-primary/10"}`}
          >
            {fileName ? (
              <CheckCircle2 aria-hidden="true" className="h-6 w-6 text-primary" />
            ) : (
              <FileUp aria-hidden="true" className="h-6 w-6 text-primary" />
            )}
            <span className="font-medium">
              {fileName ? <>Read <span className="text-primary">{fileName}</span> — drop another file to replace it</> : <>Drop your CV here or <span className="text-primary underline underline-offset-2">browse</span></>}
            </span>
            <span className="text-xs text-muted-foreground">PDF or DOCX, up to 5 MiB. We extract the text; the file itself is not stored.</span>
            <input
              type="file"
              accept={RESUME_ACCEPT}
              className="sr-only"
              onChange={(e) => { void onResumeFile(e.target.files?.[0]); e.target.value = ""; }}
            />
          </label>
        )}

        <label className="block space-y-2 text-sm font-medium">
          <span>Resume text</span>
          <Textarea
            value={profile.resume}
            onChange={(e) => update("resume", e.target.value)}
            maxLength={10000}
            rows={12}
            disabled={parsing}
            placeholder="Paste your resume here, or upload a file above to fill this in automatically."
            className="min-h-60 resize-y"
            aria-describedby="resume-length"
          />
          <span id="resume-length" className="block text-right text-xs font-normal text-muted-foreground">
            {profile.resume.length.toLocaleString()} / 10,000 characters
          </span>
        </label>
      </section>

      <div className="sticky bottom-4 z-10 flex flex-wrap items-center gap-3 rounded-2xl border border-border/30 bg-background/80 p-3 backdrop-blur">
        <Button type="submit" disabled={save.isPending || parsing || (!dirty && !!data)} className="glow-button px-6">
          {save.isPending && <Loader2 aria-hidden="true" className="mr-2 h-4 w-4 animate-spin" />}
          {save.isPending ? "Saving…" : "Save profile"}
        </Button>
        <span aria-live="polite" className="text-sm text-muted-foreground">
          {dirty ? "Unsaved changes" : data ? "All changes saved" : ""}
        </span>
        {data && !dirty && (
          <Link href="/dashboard" className="ml-auto inline-flex items-center gap-2 rounded-xl border border-primary/30 px-5 py-2 text-sm font-medium text-primary hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
            Choose an interview <ArrowRight aria-hidden="true" className="h-4 w-4" />
          </Link>
        )}
      </div>
    </form>
  );
}
