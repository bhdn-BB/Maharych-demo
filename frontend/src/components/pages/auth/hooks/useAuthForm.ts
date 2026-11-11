import { useRouter } from "next/navigation";
import { signIn } from "next-auth/react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { loginSchema, registerSchema } from "@/lib/auth-schemas";
import { authApi } from "@/api/auth/auth.api";
import type { FormValues } from "../types/auth.types";

export function useAuthForm(mode: "login" | "register") {
  const router = useRouter();
  const isLogin = mode === "login";
  const schema = isLogin ? loginSchema : registerSchema;

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      email: "",
      password: "",
      ...(isLogin ? {} : { confirmPassword: "" }),
    },
  });

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      if (!isLogin) {
        await authApi.register(values.email, values.password);
      }

      const result = await signIn("credentials", {
        email: values.email,
        password: values.password,
        redirect: false,
      });

      if (result?.error) {
        throw new Error(
          isLogin
            ? "Invalid email or password"
            : "Sign in failed after registration",
        );
      }
    },
    onSuccess: () => {
      if (!isLogin) {
        toast.success("Account created successfully!");
      }
      router.push(isLogin ? "/dashboard" : "/profile");
    },
  });

  return {
    form,
    error: mutation.error?.message ?? "",
    loading: mutation.isPending,
    isLogin,
    onSubmit: (values: FormValues) => mutation.mutate(values),
  };
}
