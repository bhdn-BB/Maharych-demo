import { motion } from "framer-motion";

interface AuthFormErrorProps {
  error: string;
}

export function AuthFormError({ error }: AuthFormErrorProps) {
  if (!error) return null;

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      className="bg-destructive/10 border border-destructive/20 text-destructive rounded-xl p-3 mb-4 text-sm text-center"
    >
      {error}
    </motion.div>
  );
}
