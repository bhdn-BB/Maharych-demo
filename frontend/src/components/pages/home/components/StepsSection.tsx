import { motion } from "framer-motion";
import { steps } from "../utils/data";
import { fadeUp } from "../utils/animations";

export function StepsSection() {
  return (
    <section className="py-24 px-6">
      <div className="container mx-auto">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <motion.h2
            variants={fadeUp}
            custom={0}
            className="font-display text-3xl md:text-5xl font-bold"
          >
            How It <span className="gradient-text">Works</span>
          </motion.h2>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          {steps.map((s, i) => (
            <motion.div
              key={s.num}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.15, duration: 0.5 }}
              className="text-center"
            >
              <div className="w-16 h-16 rounded-2xl glass mx-auto mb-5 flex items-center justify-center glow-border">
                <s.icon className="w-7 h-7 text-primary" />
              </div>
              <span className="text-xs text-primary font-semibold tracking-widest">
                {s.num}
              </span>
              <h3 className="font-display text-lg font-semibold mt-2 mb-2">
                {s.title}
              </h3>
              <p className="text-sm text-muted-foreground">{s.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
