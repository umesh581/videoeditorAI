// facedetect <image>... → one JSON line per image: {"path": ..., "faces": [[x, y, w, h], ...]}
// Boxes are normalized 0..1 with a TOP-left origin (Vision's is bottom-left).
import Foundation
import Vision
import ImageIO

for path in CommandLine.arguments.dropFirst() {
    var faces: [[Double]] = []
    if let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
       let img = CGImageSourceCreateImageAtIndex(src, 0, nil) {
        let req = VNDetectFaceRectanglesRequest()
        try? VNImageRequestHandler(cgImage: img, options: [:]).perform([req])
        for f in req.results ?? [] where f.confidence > 0.5 {
            let b = f.boundingBox
            let box: [Double] = [Double(b.minX), 1.0 - Double(b.maxY), Double(b.width), Double(b.height)]
            faces.append(box.map { (v: Double) -> Double in (v * 1000.0).rounded() / 1000.0 })
        }
    }
    let obj: [String: Any] = ["path": path, "faces": faces]
    let data = try! JSONSerialization.data(withJSONObject: obj)
    print(String(data: data, encoding: .utf8)!)
}
