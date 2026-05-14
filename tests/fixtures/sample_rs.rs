use std::collections::HashMap;

pub struct Config {
    values: HashMap<String, String>,
}

pub enum Status {
    Active,
    Inactive,
    Pending,
}

pub trait Processor {
    fn process(&self, input: &str) -> String;
    fn reset(&mut self);
}

impl Config {
    pub fn new() -> Self {
        Config { values: HashMap::new() }
    }

    pub fn get(&self, key: &str) -> Option<&String> {
        self.values.get(key)
    }

    pub fn set(&mut self, key: String, value: String) {
        self.values.insert(key, value);
    }
}

pub fn parse_config(input: &str) -> Config {
    let mut cfg = Config::new();
    for line in input.lines() {
        if let Some((k, v)) = line.split_once('=') {
            cfg.set(k.trim().to_string(), v.trim().to_string());
        }
    }
    cfg
}
