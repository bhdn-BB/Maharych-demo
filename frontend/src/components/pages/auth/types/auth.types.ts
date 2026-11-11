export interface AuthFormProps {
  mode: "login" | "register";
}

export type FormValues = {
  email: string;
  password: string;
  confirmPassword?: string;
};
