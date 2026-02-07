use minifb::{Window, WindowOptions};
use pyo3::prelude::*;
use simple_3d::{camera::Camera, engine::Engine, scene::Scene, shape::{AngleUnit, cube::Cube}};
use simple_linear_algebra::vector::{Axis, AxisUnits, vec3::Vec3};
use simple_render::{color::Color, render::buffer::BufferSize};

#[pyfunction]
pub fn init() -> PyResult<()> {
    let cube1 = Cube::new(Vec3::Z * 3.0, 3.0);
    let cube2 = Cube::new(Vec3::Z * 4.0 + Vec3::X * 3.0 + Vec3::Y * 2.0, 1.2);

    let size = BufferSize::new(1000, 1000);

    let angles = [AngleUnit::new(Axis::X, 0.5), AngleUnit::new(Axis::Y, 0.5), AngleUnit::new(Axis::Z, 0.5)];
    //let matrix = Matrix4::UNIT;

    let mut option = WindowOptions::default();
    option.resize = true;
    let window = Window::new("Test", size.width, size.height, option).unwrap();

    let camera = Camera::default();
    //camera.pos = Vec3::splat(0.1);
    //camera = camera.rotate(&[AngleUnit::new(Axis::X, 10.0), AngleUnit::new(Axis::Y, 10.0), AngleUnit::new(Axis::Z, 10.0)]);

    let scene = Scene::new(vec![cube1.create(), cube2.create()], camera);

    let engine = Engine::new(scene, Color::WHITE, &angles, size);

    engine.run(120.0, window);

    Ok(())
}

/// A Python module implemented in Rust.
#[pymodule]
pub fn lfm_lib(m: &Bound<'_, PyModule>) ->PyResult<()> {
    m.add_function(wrap_pyfunction!(init, m)?)?;
    Ok(())
}
