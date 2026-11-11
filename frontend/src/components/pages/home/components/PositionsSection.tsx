import { motion } from "framer-motion";
import { positions } from "../utils/data";
import { fadeUp } from "../utils/animations";

export function PositionsSection({
  selected,
  onSelect,
}: {
  selected: string;
  onSelect: (position: string) => void;
}) {
  return (
    <section className="py-10 px-6">
      <div className="container mx-auto">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="text-center mb-8"
        >
          <motion.h2
            variants={fadeUp}
            custom={0}
            className="font-display text-3xl md:text-5xl font-bold"
          >
            Pick Your <span className="gradient-text">Position</span>
          </motion.h2>
          <motion.p
            variants={fadeUp}
            custom={1}
            className="mt-4 text-muted-foreground max-w-lg mx-auto"
          >
            Select a role to see a sample question
          </motion.p>
        </motion.div>

        <div className="flex flex-wrap justify-center gap-4 max-w-3xl mx-auto">
          {positions.map((p, i) => (
            <motion.div
              key={p.label}
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05, duration: 0.4 }}
              whileHover={{ scale: 1.05 }}
            >
              <button
                type="button"
                aria-pressed={selected === p.label}
                onClick={() => onSelect(p.label)}
                className={`glass flex items-center gap-3 rounded-full px-6 py-3 transition-colors hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${selected === p.label ? "border-primary/70 bg-primary/10 glow-border" : ""}`}
              >
                <p.icon className="w-4 h-4 text-primary" />
                <span className="text-sm font-medium">{p.label}</span>
              </button>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
