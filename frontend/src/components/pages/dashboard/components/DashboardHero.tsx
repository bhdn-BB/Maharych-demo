import { motion } from "framer-motion";
import { fadeUp } from "../utils/animations";

export function DashboardHero() {
  return (
    <section className="pt-24 pb-8 px-6 text-center">
      <motion.div initial="hidden" animate="visible">
        <motion.h1
          variants={fadeUp}
          custom={0}
          className="font-display text-4xl md:text-5xl font-bold"
        >
          Choose Your <span className="gradient-text">Interview</span>
        </motion.h1>
        <motion.p
          variants={fadeUp}
          custom={1}
          className="mt-4 text-muted-foreground max-w-lg mx-auto"
        >
          Browse options and build your perfect mock interview session
        </motion.p>
      </motion.div>
    </section>
  );
}
