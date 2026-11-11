import { motion } from "framer-motion";
import { levels } from "../utils/data";
import { fadeUp } from "../utils/animations";

export function LevelsSection({
  selected,
  onSelect,
}: {
  selected: string;
  onSelect: (level: string) => void;
}) {
  return (
    <section className="pb-6 pt-14 px-6">
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
            Choose Your <span className="gradient-text">Level</span>
          </motion.h2>
          <motion.p
            variants={fadeUp}
            custom={1}
            className="mt-4 text-muted-foreground max-w-lg mx-auto"
          >
            Choose a level to preview a question for your experience
          </motion.p>
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 max-w-5xl mx-auto">
          {levels.map((l) => (
            <motion.div
              key={l.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: l.delay, duration: 0.5 }}
              whileHover={{ y: -6, transition: { duration: 0.2 } }}
              className="h-full"
            >
              <button
                type="button"
                aria-pressed={selected === l.title}
                onClick={() => onSelect(l.title)}
                className={`glass group h-full w-full rounded-2xl p-6 text-left transition-colors duration-300 hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${selected === l.title ? "border-primary/70 bg-primary/10 glow-border" : ""}`}
              >
                <div className="w-12 h-12 rounded-xl bg-primary/15 flex items-center justify-center mb-4 group-hover:bg-primary/25 transition-colors">
                  <l.icon className="w-6 h-6 text-primary" />
                </div>
                <h3 className="font-display text-xl font-semibold mb-2">
                  {l.title}
                </h3>
                <p className="text-sm text-muted-foreground">{l.desc}</p>
              </button>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
