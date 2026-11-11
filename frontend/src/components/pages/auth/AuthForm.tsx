"use client";

import { motion } from "framer-motion";
import { useAuthForm } from "./hooks/useAuthForm";
import { AuthFormHeader } from "./components/AuthFormHeader";
import { AuthFormError } from "./components/AuthFormError";
import { AuthFormFields } from "./components/AuthFormFields";
import { GoogleAuthButton } from "./components/GoogleAuthButton";
import type { AuthFormProps } from "./types/auth.types";

export function AuthForm({ mode }: AuthFormProps) {
  const { form, error, loading, isLogin, onSubmit } = useAuthForm(mode);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="glass rounded-3xl p-8 glow-border">
        <AuthFormHeader isLogin={isLogin} />
        <AuthFormError error={error} />
        <AuthFormFields
          form={form}
          isLogin={isLogin}
          loading={loading}
          onSubmit={onSubmit}
        />
        <GoogleAuthButton />
      </div>
    </motion.div>
  );
}
