interface AuthFormHeaderProps {
  isLogin: boolean;
}

export function AuthFormHeader({ isLogin }: AuthFormHeaderProps) {
  return (
    <div className="text-center mb-6">
      <h1 className="text-2xl font-bold font-['Space_Grotesk']">
        {isLogin ? "Welcome back" : "Create your account"}
      </h1>
      <p className="text-muted-foreground mt-1">
        {isLogin
          ? "Sign in to continue your interview prep"
          : "Start practicing for your next interview"}
      </p>
    </div>
  );
}
